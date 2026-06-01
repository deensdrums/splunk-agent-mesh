"""Agent orchestrator.

Runs the primary (user-visible) agents and exposes the sub-agent lookup those
agents delegate to via handoff. The shipping mesh has one primary agentic agent
(the Threat Hunter) plus one reporting sub-agent.
"""

from __future__ import annotations

import logging
from typing import Callable

from ..conf_reader import ConfReader
from ..demo.demo_case import build_demo_result
from ..investigation_models import audit_event, markdown_section, now_iso
from ..llm.base import LLMProvider
from ..request_context import RequestContext
from ..splunk_client import SplunkClient
from .agentic_llm_agent import AgenticLLMAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        conf_reader: ConfReader,
        llm_provider: LLMProvider | None = None,
        context: RequestContext | None = None,
        splunk_client_factory: Callable[[], SplunkClient | None] | None = None,
    ):
        self.conf_reader = conf_reader
        self.llm = llm_provider
        self.context = context or RequestContext(username="dev-user")
        self.splunk_client_factory = splunk_client_factory or (lambda: None)

    def get_agent_descriptors(self) -> list[dict]:
        """Public-facing list of user-visible agents (no system prompts).

        Sub-agents (e.g. the reporting agent) are intentionally excluded — they
        are delegated internal capabilities, never shown as top-level peers.
        """
        return [
            {
                "id": a.id,
                "display_name": a.display_name,
                "description": a.description,
                "order": a.order,
                "enabled": a.enabled,
                "skills": a.skills,
            }
            for a in self.conf_reader.get_agents()
            if a.agent_role == "primary"
        ]

    def run(
        self,
        request: dict,
        investigation_id: str | None = None,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        all_agents = self.conf_reader.get_agents()
        # Only primary agents are executed top-level and shown in the UI.
        # Sub-agents are looked up by id and delegated to by primary agents.
        agents = [a for a in all_agents if a.agent_role == "primary"]
        subagents = {a.id: a for a in all_agents if a.agent_role == "subagent"}
        agent_order = [a.id for a in agents]
        run_id = investigation_id or request.get("investigation_id", "inv-001")

        if request.get("demo"):
            logger.info("Demo mode: returning canned threat-hunter events.")
            return build_demo_result(agents, investigation_id=run_id, owner=self.context.username)

        started = now_iso()
        outputs: dict[str, dict] = {}
        artifacts: list[dict] = []
        sections: list[dict] = []
        audit: list[dict] = [
            audit_event("orchestration_started", run_id, self.context.username, agent_count=len(agents))
        ]

        for cfg in agents:
            if self.llm is None:
                output, agent_artifacts = self._no_llm_output(cfg), []
            else:
                agentic_agent = AgenticLLMAgent(cfg, self.llm, self.splunk_client_factory, subagents)

                def _iteration_cb(
                    intermediate_output: dict,
                    new_artifacts: list[dict],
                    _cfg_id: str = cfg.id,
                ) -> None:
                    if progress_callback:
                        progress_callback({
                            "agent_order": agent_order,
                            "agents": {_cfg_id: intermediate_output},
                            "artifacts": new_artifacts,
                            "sections": [],
                            "audit": [],
                        })

                output, agent_artifacts = agentic_agent.run(request, progress_callback=_iteration_cb)

            output["artifacts"] = [a["id"] for a in agent_artifacts]
            outputs[cfg.id] = output
            artifacts.extend(agent_artifacts)
            agent_sections = []
            if output.get("markdown"):
                agent_sections.append(
                    markdown_section(
                        f"section-{cfg.id}",
                        cfg.display_name,
                        output["markdown"],
                        agent_id=cfg.id,
                    )
                )
                sections.extend(agent_sections)
            agent_audit = audit_event(
                "agent_completed",
                run_id,
                self.context.username,
                status=output.get("status", "completed"),
                agent_id=cfg.id,
                artifact_count=len(agent_artifacts),
            )
            audit.append(agent_audit)
            if progress_callback:
                progress_callback(
                    {
                        "agent_order": agent_order,
                        "agents": {cfg.id: output},
                        "sections": agent_sections,
                        "artifacts": agent_artifacts,
                        "audit": [agent_audit],
                    }
                )

        return {
            "id": run_id,
            "owner": self.context.username,
            "status": "complete",
            "started_at": started,
            "completed_at": now_iso(),
            "agent_order": agent_order,
            "agents": outputs,
            "sections": sections,
            "artifacts": artifacts,
            "audit": audit,
        }

    def _no_llm_output(self, cfg) -> dict:
        """Error output for a primary agent when no LLM provider is configured."""
        ts = now_iso()
        return {
            "agent_id": cfg.id,
            "display_name": cfg.display_name,
            "status": "error",
            "events": [],
            "markdown": "_No LLM provider configured. Save an API key on the Settings tab._",
            "model": cfg.model,
            "started_at": ts,
            "completed_at": ts,
            "error": "No LLM provider configured.",
        }
