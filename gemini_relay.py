import json, os, re, time, urllib.parse, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import httpx

PRIMARY = "gemini-3.1-flash-lite"
FALLBACKS = ["gemini-3-flash-preview", "gemini-3.5-flash"]
HOST = "https://generativelanguage.googleapis.com"
PORT = 18080


def _log(msg: str):
    print(f"[relay] {msg}", flush=True)


def _sleep_from_429(body: bytes) -> float:
    try:
        info = json.loads(body)
        for d in info.get("error", {}).get("details", []):
            rd = d.get("retryDelay", "")
            m = re.search(r"(\d+(?:\.\d+)?)s", rd)
            if m:
                return float(m.group(1))
    except Exception:
        pass
    return 5


class RelayHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        auth = self.headers.get("Authorization", "")

        _log(f"<< {self.path}  auth={'yes' if auth else 'no'}")

        # Determine if this is OpenAI format or native format
        is_openai = "/chat/completions" in self.path or "/api/" in self.path

        # Parse body to get model
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}

        current_model = payload.get("model", PRIMARY) if is_openai else _extract_model(self.path)
        _log(f"   model={current_model} format={'openai' if is_openai else 'native'}")

        models = [PRIMARY] + FALLBACKS
        if current_model in models:
            start = models.index(current_model)
        else:
            start = 0

        for i in range(start, len(models)):
            model = models[i]
            upstream_headers = {"Content-Type": "application/json"}

            if is_openai:
                upstream_headers["Authorization"] = auth
                new_payload = dict(payload)
                new_payload["model"] = model
                new_body = json.dumps(new_payload).encode()
                # OpenAI endpoint: /v1beta/openai/chat/completions
                path = self.path
                # If path is /v1beta/..., add /openai after /v1beta
                if path.startswith("/v1beta/") and not path.startswith("/v1beta/openai/"):
                    path = path.replace("/v1beta/", "/v1beta/openai/", 1)
                url = f"{HOST}{path}"
            else:
                # Native format: extract key from auth or query
                if auth.startswith("Bearer "):
                    upstream_headers["X-Goog-Api-Key"] = auth.removeprefix("Bearer ").strip()
                qkey = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("key", [None])[0]
                if qkey:
                    upstream_headers["X-Goog-Api-Key"] = qkey
                new_body = body
                path = re.sub(r"/models/[^:?]+", f"/models/{model}", self.path)
                url = f"{HOST}{path}"

            try:
                with httpx.Client(http2=True, timeout=120) as c:
                    r = c.post(url, content=new_body, headers=upstream_headers)
            except Exception as e:
                _log(f"EXCEPTION: {e}")
                self.send_error(502, json.dumps({"error": str(e)}))
                return

            _log(f">> {model} = {r.status_code}")

            # If 400 on native with X-Goog-Api-Key, retry with ?key= query param
            if not is_openai and r.status_code == 400 and "X-Goog-Api-Key" in upstream_headers:
                k = upstream_headers.pop("X-Goog-Api-Key")
                url2 = f"{url.split('?')[0]}?key={urllib.parse.quote(k)}"
                try:
                    r = c.post(url2, content=body, headers=upstream_headers)
                except Exception as e:
                    self.send_error(502, json.dumps({"error": str(e)}))
                    return
                _log(f">> {model} (?key) = {r.status_code}")

            if r.status_code == 429 and i < len(models) - 1:
                wait = _sleep_from_429(r.content)
                _log(f"429 on {model} -> {models[i+1]} after {wait:.0f}s")
                time.sleep(min(wait, 30))
                continue

            self.send_response(r.status_code)
            for h in ("content-type",):
                if h in r.headers:
                    self.send_header(h, r.headers[h])
            self.end_headers()
            self.wfile.write(r.content)
            return

        self.send_error(502, json.dumps({"error": "all models rate limited"}))

    def log_message(self, fmt, *args):
        pass


def _extract_model(path: str) -> str:
    m = re.search(r"/models/([^:?]+)", path)
    return m.group(1) if m else PRIMARY


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), RelayHandler)
    _log(f"Relay on http://127.0.0.1:{PORT}")
    _log(f"  Primary: {PRIMARY}  Fallbacks: {FALLBACKS}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log("shutdown")
        server.server_close()


if __name__ == "__main__":
    main()
