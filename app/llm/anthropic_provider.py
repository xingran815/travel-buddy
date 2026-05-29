"""Anthropic (Claude) implementation of the ``LLMProvider`` protocol."""

import os

from app.llm.base import LLMResult, LLMUsage


class AnthropicProvider:
    """Claude-backed provider using the ``anthropic`` Messages API.

    Unlike the OpenAI chat format, Anthropic takes the system prompt as a
    separate argument and has no native JSON mode, so ``_split_system`` extracts
    the system text and ``_call`` appends an explicit JSON instruction when JSON
    output is requested. The ``anthropic`` package is imported lazily so it's
    only required when this provider is selected."""

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
        """Separate the OpenAI-style ``system`` messages from the rest.

        Returns ``(joined_system_text_or_None, non_system_messages)``."""
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
        """Call the Messages API and wrap the reply (with token usage) in ``LLMResult``."""
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
        """Generate free-form prose."""
        return self._call(messages, temperature, model, json_mode=False)

    def chat_json(self, messages: list[dict], temperature: float = 0.1, model: str | None = None) -> LLMResult:
        """Generate a JSON object (instruction appended to the system prompt)."""
        return self._call(messages, temperature, model, json_mode=True)
