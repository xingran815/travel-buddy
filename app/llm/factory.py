"""Select the LLM backend from the ``LLM_PROVIDER`` config setting."""

from app.config import LLM_PROVIDER
from app.llm.base import LLMProvider


def get_provider() -> LLMProvider:
    """Instantiate the configured provider (openai/anthropic/ollama).

    Providers are imported lazily so only the selected backend's SDK needs to be
    installed. Raises ``ValueError`` for an unrecognised ``LLM_PROVIDER``."""
    name = (LLM_PROVIDER or "openai").lower()
    if name == "openai":
        from app.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "ollama":
        from app.llm.ollama_provider import OllamaProvider
        return OllamaProvider()
    raise ValueError(
        f"Unknown LLM_PROVIDER {name!r}. Set LLM_PROVIDER to one of: openai, anthropic, ollama."
    )
