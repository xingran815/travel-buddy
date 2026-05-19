from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class LLMResult:
    text: str
    usage: LLMUsage | None = None


class LLMProvider(Protocol):
    def chat_text(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        model: str | None = None,
    ) -> LLMResult: ...

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        model: str | None = None,
    ) -> LLMResult: ...
