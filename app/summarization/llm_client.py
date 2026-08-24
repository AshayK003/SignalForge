import threading
import time
from typing import Any

import httpx

_MAX_RETRIES = 5
_MAX_RETRY_WAIT = 10


class _RateLimiter:
    def __init__(self, rpm: int = 20):
        self.min_interval = 60.0 / max(rpm, 1)
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_call = time.monotonic()


class LLMClient:
    def __init__(self, config: Any, logger: Any = None):
        self.config = config
        self.log = logger.info if logger else None
        self._limiter = _RateLimiter(rpm=getattr(config.llm, "max_rpm", 20))

    def _provider_base_url(self, provider: str) -> str:
        if provider == "ollama":
            return f"{self.config.llm.ollama_base_url.rstrip('/')}/v1"
        if provider == "deepseek":
            return "https://api.deepseek.com/v1"
        return "https://openrouter.ai/api/v1"

    def _provider_model(self, provider: str) -> str:
        if provider == "ollama":
            return self.config.llm.ollama_model
        if provider == "deepseek":
            return self.config.llm.deepseek_model
        return self.config.llm.openrouter_model

    def _headers_for(self, provider: str) -> dict:
        headers = {"Content-Type": "application/json"}
        if provider == "openrouter":
            headers["Authorization"] = f"Bearer {self.config.llm.openrouter_api_key}"
            headers["HTTP-Referer"] = "http://localhost:8501"
            headers["X-Title"] = "SignalForge"
        if provider == "deepseek":
            headers["Authorization"] = f"Bearer {self.config.llm.deepseek_api_key}"
        return headers

    def _post_gemini(self, messages: list[dict], temperature: float, max_tokens: int, json_mode: bool) -> str:
        """Gemini generateContent API (different wire shape from OpenAI-compatible providers)."""
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.config.llm.gemini_model}:generateContent"
        )
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        contents = [
            {"role": m["role"], "parts": [{"text": m["content"]}]}
            for m in messages
            if m["role"] != "system"
        ]
        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_parts:
            payload["system_instruction"] = {"parts": [{"text": chr(10).join(system_parts)}]}
        if json_mode:
            payload["generationConfig"]["response_mime_type"] = "application/json"

        last_error: Exception | None = None
        for attempt in range(3):
            self._limiter.wait()
            try:
                resp = httpx.post(
                    url,
                    headers={"x-goog-api-key": self.config.llm.gemini_api_key},
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 429:
                    wait = 5 * (2**attempt)
                    self._log(f"Gemini rate limited — waiting {wait}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:  # noqa: BLE001 - narrow to RuntimeError at the boundary
                last_error = e
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise RuntimeError(f"Gemini API error: {e}") from e
        raise RuntimeError(f"Gemini API failed after retries: {last_error}")

    def _fallback_provider(self) -> str | None:
        primary = self.config.llm.provider
        if primary == "openrouter":
            return "ollama"
        if primary == "ollama" and self.config.llm.openrouter_api_key:
            return "openrouter"
        if primary == "deepseek":
            return "ollama"
        return None

    def _wait_for_rate_limit(self, resp_headers: dict):
        wait = _MAX_RETRY_WAIT
        reset_val = resp_headers.get("X-RateLimit-Reset")
        if reset_val:
            try:
                reset_ts = int(reset_val) / 1000
                remaining = reset_ts - time.time()
                if 1 < remaining < _MAX_RETRY_WAIT:
                    wait = remaining + 1
            except (ValueError, TypeError):
                pass
        if self.log:
            self.log(f"Rate limited — waiting {wait:.0f}s")
        time.sleep(wait)

    def _post(self, provider: str, payload: dict) -> httpx.Response:
        with httpx.Client(timeout=120.0) as client:
            return client.post(
                f"{self._provider_base_url(provider)}/chat/completions",
                headers=self._headers_for(provider),
                json=payload,
            )

    def _log(self, msg: str):
        if self.log:
            self.log(msg)

    def _attempt_call(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        response_format: dict | None,
        provider: str,
        max_retries: int = _MAX_RETRIES,
    ) -> str:
        model = self._provider_model(provider)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format and provider in ("openrouter", "deepseek"):
            payload["response_format"] = response_format

        self._log(f"LLM call ({provider}/{model}): {len(messages)} messages")

        last_error = None
        for attempt in range(max_retries):
            self._limiter.wait()
            if attempt > 0 and self.log:
                self.log(f"LLM retry {attempt + 1}/{max_retries} ({provider}/{model}): {last_error}")
            try:
                resp = self._post(provider, payload)

                if resp.status_code == 429:
                    last_error = "HTTP 429 (rate limited)"
                    if attempt < max_retries - 1:
                        self._wait_for_rate_limit(resp.headers)
                        continue
                    raise RuntimeError(f"Rate limited after {max_retries} retries ({provider}/{model}): {resp.text}")

                if resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}"
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)
                        continue
                    raise RuntimeError(
                        f"Server error after {max_retries} retries ({provider}/{model}): {resp.status_code}: {resp.text}"
                    )

                if resp.status_code != 200:
                    raise RuntimeError(f"API error ({provider}/{model}): {resp.status_code}: {resp.text}")

                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                self._log(f"LLM response: {usage.get('total_tokens', '?')} tokens ({provider}/{model})")
                return content

            except httpx.TimeoutException as e:
                last_error = f"timeout ({e})"
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                raise RuntimeError(f"Timeout after {max_retries} retries ({provider}/{model}): {e}") from e

        raise RuntimeError(f"Failed after {max_retries} retries ({provider}/{model}): {last_error}")

    def _ollama_alive(self) -> bool:
        try:
            with httpx.Client(timeout=3.0) as c:
                r = c.get(f"{self.config.llm.ollama_base_url.rstrip('/')}/api/tags")
            return r.status_code == 200
        except Exception:
            return False

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        # Try providers in order: configured primary → keyed remotes → ollama
        primary = self.config.llm.provider
        providers = [primary]
        for p in ("openrouter", "deepseek", "gemini"):
            if p == primary:
                continue
            key = {
                "openrouter": self.config.llm.openrouter_api_key,
                "deepseek": self.config.llm.deepseek_api_key,
                "gemini": self.config.llm.gemini_api_key,
            }.get(p)
            if key:
                providers.append(p)
        if "ollama" not in providers:
            providers.append("ollama")

        json_mode = bool(response_format)
        last_error = None
        for provider in providers:
            is_remote = provider in ("openrouter", "deepseek")
            max_retry = 1 if is_remote else _MAX_RETRIES
            if provider == "ollama" and not self._ollama_alive():
                self._log("Ollama not reachable — skipping")
                continue
            try:
                if provider == "gemini":
                    return self._post_gemini(messages, temperature, max_tokens, json_mode)
                return self._attempt_call(
                    messages, temperature, max_tokens, response_format, provider, max_retries=max_retry
                )
            except RuntimeError as e:
                last_error = e
                self._log(f"{provider} failed — trying next: {e}")

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    def supports_json_mode(self) -> bool:
        return self.config.llm.provider in ("openrouter", "deepseek", "gemini")
