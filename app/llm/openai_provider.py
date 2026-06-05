"""OpenAI-compatible implementation of the ``LLMProvider`` protocol.

Works with the OpenAI API and any compatible endpoint via ``LLM_BASE_URL``
(e.g. Azure, OpenRouter, local gateways), which is why the model and base URL
are configurable rather than hard-coded.
"""

from openai import OpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from app.llm.base import LLMResult, LLMUsage


class OpenAIProvider:
    """Chat-completions provider using the official ``openai`` client."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        self.client = OpenAI(api_key=api_key or LLM_API_KEY, base_url=base_url or LLM_BASE_URL)
        self.default_model = model or LLM_MODEL

    def _call(self, messages: list[dict], temperature: float, model: str | None, json_mode: bool) -> LLMResult:
        """Call chat completions and wrap the reply (with token usage) in ``LLMResult``.

        Sets ``response_format={"type": "json_object"}`` when ``json_mode``."""
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        usage = None
        raw_usage = getattr(response, "usage", None)
        if raw_usage is not None:
            usage = LLMUsage(
                prompt_tokens=int(getattr(raw_usage, "prompt_tokens", 0) or 0),
                completion_tokens=int(getattr(raw_usage, "completion_tokens", 0) or 0),
            )
        text = response.choices[0].message.content or ""
        return LLMResult(text=text, usage=usage)

    def chat_text(self, messages: list[dict], temperature: float = 0.3, model: str | None = None) -> LLMResult:
        """Generate free-form prose."""
        return self._call(messages, temperature, model, json_mode=False)

    def chat_json(self, messages: list[dict], temperature: float = 0.1, model: str | None = None) -> LLMResult:
        """Generate a JSON object using the API's JSON response format."""
        return self._call(messages, temperature, model, json_mode=True)
