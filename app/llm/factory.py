from app.config import LLM_PROVIDER
from app.llm.base import LLMProvider


def get_provider() -> LLMProvider:
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
