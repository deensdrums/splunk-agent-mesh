"""OpenRouter provider (OpenAI-compatible API)."""

from .openai_compatible_provider import OpenAICompatibleProvider

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        super().__init__(api_key=api_key, base_url=DEFAULT_BASE_URL, model=model)

    def _default_model(self) -> str:
        return DEFAULT_MODEL
