"""Anthropic Claude provider."""

import time
import logging
from .base import LLMProvider, Message, CompletionResponse, ToolCall, ToolUseResponse

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> CompletionResponse:
        try:
            import anthropic  # type: ignore
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        target_model = model or self.model

        system_messages = [m for m in messages if m.role == "system"]
        other_messages = [m for m in messages if m.role != "system"]

        system = system_messages[0].content if system_messages else None
        api_messages = [{"role": m.role, "content": m.content} for m in other_messages]

        kwargs: dict = {
            "model": target_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return CompletionResponse(
            content=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> ToolUseResponse:
        try:
            import anthropic  # type: ignore
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        target_model = model or self.model

        kwargs: dict = {
            "model": target_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "tools": tools,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)

        text_parts = []
        tool_calls = []
        raw_content = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                raw_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))
                raw_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return ToolUseResponse(
            content_text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            raw_content=raw_content,
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
