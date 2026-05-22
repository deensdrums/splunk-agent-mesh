"""OpenAI-compatible provider (works with OpenAI, Azure OpenAI, local LLMs, etc.)."""

import time
import logging
from .base import LLMProvider, Message, CompletionResponse

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o"


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> CompletionResponse:
        try:
            import openai  # type: ignore
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        target_model = model or self.model

        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = client.chat.completions.create(
            model=target_model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return CompletionResponse(
            content=choice.message.content or "",
            model=response.model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )

    def test_connection(self) -> dict:
        start = time.monotonic()
        try:
            result = self.complete(
                messages=[Message(role="user", content="Reply with the word OK only.")],
                max_tokens=5,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            return {"success": True, "latency_ms": latency_ms, "model": result.model, "error": None}
        except Exception as e:
            return {"success": False, "latency_ms": None, "model": None, "error": str(e)}

    def _default_model(self) -> str:
        return DEFAULT_MODEL
