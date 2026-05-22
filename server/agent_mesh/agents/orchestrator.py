"""Agent orchestrator. Reads enabled agents from agents.conf and runs each one.

Agents are independent in v1: each sees only the original request, not other
agents' outputs. They run sequentially server-side (a parallel implementation
would be a straightforward future improvement).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..conf_reader import ConfReader
from ..demo.demo_case import build_demo_result
from ..llm.base import LLMProvider
from .llm_agent import LLMAgent

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Orchestrator:
    def __init__(self, conf_reader: ConfReader, llm_provider: LLMProvider | None = None):
        self.conf_reader = conf_reader
        self.llm = llm_provider

    def get_agent_descriptors(self) -> list[dict]:
        """Public-facing list of configured agents (no system prompts)."""
        return [
            {
                "id": a.id,
                "display_name": a.display_name,
                "description": a.description,
                "order": a.order,
                "enabled": a.enabled,
            }
            for a in self.conf_reader.get_agents()
        ]

    def run(self, request: dict) -> dict:
        agents = self.conf_reader.get_agents()
        agent_order = [a.id for a in agents]

        if request.get("demo"):
            logger.info("Demo mode: returning canned per-agent markdown.")
            return build_demo_result(agents)

        started = _now_iso()
        outputs: dict[str, dict] = {}
        for cfg in agents:
            agent = LLMAgent(cfg, self.llm)
            outputs[cfg.id] = agent.run(request)

        return {
            "id": request.get("investigation_id", "inv-001"),
            "status": "complete",
            "started_at": started,
            "completed_at": _now_iso(),
            "agent_order": agent_order,
            "agents": outputs,
        }
