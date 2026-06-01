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
    agent_mode: str = "single_shot"
    max_iterations: int = 10
    # "primary" agents are user-visible top-level agents in the mesh.
    # "subagent" agents are delegated internal capabilities (e.g. the
    # reporting agent) invoked only by a primary agent, never shown as a peer.
    agent_role: str = "primary"
