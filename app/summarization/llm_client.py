from typing import Any

import httpx


class LLMClient:
    def __init__(self, config: Any, logger: Any = None):
        self.config = config
        self.log = logger.info if logger else None

    @property
    def _base_url(self) -> str:
        if self.config.llm.provider == "ollama":
            return f"{self.config.llm.ollama_base_url.rstrip('/')}/v1"
        return "https://openrouter.ai/api/v1"

    @property
    def _model(self) -> str:
        if self.config.llm.provider == "ollama":
            return self.config.llm.ollama_model
        return self.config.llm.openrouter_model

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.config.llm.provider == "openrouter":
            headers["Authorization"] = f"Bearer {self.config.llm.openrouter_api_key}"
            headers["HTTP-Referer"] = "http://localhost:8501"
            headers["X-Title"] = "SignalForge"
        return headers

    def chat(self, messages: list[dict], temperature: float = 0.3,
             max_tokens: int = 4096, response_format: dict | None = None) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        if self.log:
            self.log(f"LLM call: model={self._model}, messages={len(messages)}, provider={self.config.llm.provider}")

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"LLM API error {resp.status_code}: {resp.text}")

        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        usage = result.get("usage", {})
        if self.log:
            self.log(f"LLM response: {usage.get('total_tokens', '?')} tokens, "
                     f"{usage.get('total_cost', '?')} cost")

        return content

    def supports_json_mode(self) -> bool:
        return self.config.llm.provider == "openrouter"
