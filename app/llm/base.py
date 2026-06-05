"""Provider-agnostic LLM interface shared by every backend.

Concrete providers (OpenAI, Anthropic, Ollama) implement the ``LLMProvider``
protocol; the rest of the app depends only on these types, so swapping backends
is a config change. ``app/llm/factory.get_provider`` selects the implementation.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMUsage:
    """Token counts for one LLM call, used for budget accounting."""

    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class LLMResult:
    """One LLM response: the generated ``text`` plus optional token ``usage``."""

    text: str
    usage: LLMUsage | None = None


class LLMProvider(Protocol):
    """Structural interface every LLM backend must satisfy.

    ``chat_text`` returns free-form prose; ``chat_json`` requests strict JSON
    output (used by the recommendation helpers that parse the reply)."""

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
