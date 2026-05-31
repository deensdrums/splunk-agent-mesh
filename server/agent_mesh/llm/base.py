"""LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class CompletionResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class ToolUseResponse:
    content_text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    model: str
    input_tokens: int
    output_tokens: int
    raw_content: list = field(default_factory=list)


class LLMProvider(ABC):
    """Base interface for LLM providers. All providers must implement this."""

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> CompletionResponse:
        """Send messages and return a completion."""

    @abstractmethod
    def test_connection(self) -> dict:
        """
        Test the connection to the LLM API.
        Returns {"success": bool, "latency_ms": int, "model": str, "error": str | None}
        """

    def _default_model(self) -> str:
        raise NotImplementedError
