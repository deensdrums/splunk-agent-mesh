"""Agent configuration parsed from agents.conf."""

from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    id: str
    display_name: str
    description: str
    system_prompt: str
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.2
    max_tokens: int = 2048
    order: int = 100
    enabled: bool = True
    output_format: str = "markdown"
    skills: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
