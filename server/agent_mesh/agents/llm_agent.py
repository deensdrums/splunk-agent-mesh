"""Generic LLM-backed agent driven by AgentConfig from agents.conf.

Each agent is fully described by its config stanza: display name, system prompt,
model, and temperature. The agent receives only the user's request — it does not
see other agents' outputs in v1. Output is markdown.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from ..llm.base import LLMProvider, Message
from .agent_config import AgentConfig

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _format_request(request: dict) -> str:
    """Render the user request as a stable text block for the model."""
    fields = []
    for key in ("description", "host", "user", "alert_name", "time_range", "dependency_context"):
        value = request.get(key)
        if value:
            fields.append(f"{key}: {value}")
    return "\n".join(fields) if fields else json.dumps(request, indent=2)


class LLMAgent:
    """A single agent in the mesh, fully configured from agents.conf."""

    def __init__(self, config: AgentConfig, llm: LLMProvider | None):
        self.config = config
        self.llm = llm

    def run(self, request: dict) -> dict:
        started = _now_iso()
        if self.llm is None:
            return self._error_output(
                started,
                "No LLM provider configured. Save an API key on the Settings tab.",
            )

        user_msg = _format_request(request)
        messages = [
            Message(role="system", content=self.config.system_prompt),
            Message(role="user", content=user_msg),
        ]

        try:
            response = self.llm.complete(
                messages=messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return {
                "agent_id": self.config.id,
                "display_name": self.config.display_name,
                "status": "completed",
                "markdown": response.content,
                "model": response.model,
                "started_at": started,
                "completed_at": _now_iso(),
                "error": None,
            }
        except Exception as exc:
            logger.exception("Agent %s failed.", self.config.id)
            return self._error_output(started, str(exc))

    def _error_output(self, started: str, error: str) -> dict:
        return {
            "agent_id": self.config.id,
            "display_name": self.config.display_name,
            "status": "error",
            "markdown": f"_Agent failed: {error}_",
            "model": self.config.model,
            "started_at": started,
            "completed_at": _now_iso(),
            "error": error,
        }
