import os

from app.llm.base import LLMResult, LLMUsage


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None, max_tokens: int = 4096) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required for LLM_PROVIDER=anthropic. "
                "Install with: pip install anthropic"
            ) from exc
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.default_model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self.max_tokens = max_tokens

    @staticmethod
    def _split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
        system_parts: list[str] = []
        rest: list[dict] = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                if content:
                    system_parts.append(content)
            else:
                rest.append({"role": role, "content": content})
        system = "\n".join(system_parts) if system_parts else None
        return system, rest

    def _call(self, messages: list[dict], temperature: float, model: str | None, json_mode: bool) -> LLMResult:
        system, msgs = self._split_system(messages)
        if json_mode:
            json_instruction = (
                "Respond with a single valid JSON object and nothing else. "
                "Do not include markdown code fences."
            )
            system = f"{system}\n\n{json_instruction}" if system else json_instruction
        response = self.client.messages.create(
            model=model or self.default_model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system or "",
            messages=msgs,
        )
        text = "".join(getattr(block, "text", "") for block in response.content)
        usage = None
        raw_usage = getattr(response, "usage", None)
        if raw_usage is not None:
            usage = LLMUsage(
                prompt_tokens=int(getattr(raw_usage, "input_tokens", 0) or 0),
                completion_tokens=int(getattr(raw_usage, "output_tokens", 0) or 0),
            )
        return LLMResult(text=text, usage=usage)

    def chat_text(self, messages: list[dict], temperature: float = 0.3, model: str | None = None) -> LLMResult:
        return self._call(messages, temperature, model, json_mode=False)

    def chat_json(self, messages: list[dict], temperature: float = 0.1, model: str | None = None) -> LLMResult:
        return self._call(messages, temperature, model, json_mode=True)
