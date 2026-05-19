import json
import os
import urllib.error
import urllib.request

from app.llm.base import LLMResult, LLMUsage


class OllamaProvider:
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float = 120.0) -> None:
        raw = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = raw.rstrip("/")
        self.default_model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _call(self, messages: list[dict], temperature: float, model: str | None, json_mode: bool) -> LLMResult:
        payload: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "options": {"temperature": temperature},
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        body = self._post("/api/chat", payload)
        message = body.get("message") or {}
        text = message.get("content", "") or ""

        usage = None
        prompt_tokens = body.get("prompt_eval_count")
        completion_tokens = body.get("eval_count")
        if prompt_tokens is not None or completion_tokens is not None:
            usage = LLMUsage(
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
            )
        return LLMResult(text=text, usage=usage)

    def chat_text(self, messages: list[dict], temperature: float = 0.3, model: str | None = None) -> LLMResult:
        return self._call(messages, temperature, model, json_mode=False)

    def chat_json(self, messages: list[dict], temperature: float = 0.1, model: str | None = None) -> LLMResult:
        return self._call(messages, temperature, model, json_mode=True)
