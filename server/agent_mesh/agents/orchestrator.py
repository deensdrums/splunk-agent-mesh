"""Agent orchestrator.

Reads enabled agents from agents.conf, honors explicit depends_on edges, and
attaches structured artifacts for allowed tools.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Callable

from ..conf_reader import ConfReader
from ..demo.demo_case import build_demo_result
from ..investigation_models import audit_event, markdown_section, now_iso
from ..llm.base import LLMProvider
from ..request_context import RequestContext
from ..splunk_client import SplunkClient
from ..tools.splunk_search import extract_spl_blocks, run_splunk_search_artifact
from .agentic_llm_agent import AgenticLLMAgent
from .llm_agent import LLMAgent

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
        """Public-facing list of configured agents (no system prompts)."""
        return [
            {
                "id": a.id,
                "display_name": a.display_name,
                "description": a.description,
                "order": a.order,
                "enabled": a.enabled,
                "skills": a.skills,
                "depends_on": a.depends_on,
            }
            for a in self.conf_reader.get_agents()
        ]

    def run(
        self,
        request: dict,
        investigation_id: str | None = None,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        agents = self.conf_reader.get_agents()
        agent_order = [a.id for a in agents]
        run_id = investigation_id or request.get("investigation_id", "inv-001")

        if request.get("demo"):
            logger.info("Demo mode: returning canned per-agent markdown.")
            return build_demo_result(agents, investigation_id=run_id, owner=self.context.username)

        started = now_iso()
        outputs: dict[str, dict] = {}
        artifacts: list[dict] = []
        sections: list[dict] = []
        audit: list[dict] = [
            audit_event("orchestration_started", run_id, self.context.username, agent_count=len(agents))
        ]

        for cfg in self._execution_order(agents):
            dependency_context = self._dependency_context(cfg.depends_on, outputs, artifacts)
            agent_request = {**request}
            if dependency_context:
                agent_request["dependency_context"] = dependency_context

            if cfg.agent_mode == "agentic" and self.llm:
                agentic_agent = AgenticLLMAgent(cfg, self.llm, self.splunk_client_factory)

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

                output, agent_artifacts = agentic_agent.run(
                    agent_request, progress_callback=_iteration_cb,
                )
            else:
                agent = LLMAgent(cfg, self.llm)
                output = agent.run(agent_request)
                agent_artifacts = self._run_agent_tools(cfg, request, output)

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

    def _execution_order(self, agents: list) -> list:
        by_id = {a.id: a for a in agents}
        indegree = {a.id: 0 for a in agents}
        dependents: dict[str, list[str]] = {a.id: [] for a in agents}
        for agent in agents:
            for dep in agent.depends_on:
                if dep not in by_id:
                    logger.warning("Agent %s depends on unknown agent %s; ignoring.", agent.id, dep)
                    continue
                indegree[agent.id] += 1
                dependents[dep].append(agent.id)

        ready = deque(sorted([by_id[i] for i, d in indegree.items() if d == 0], key=lambda a: (a.order, a.id)))
        ordered = []
        while ready:
            agent = ready.popleft()
            ordered.append(agent)
            for child_id in sorted(dependents[agent.id], key=lambda i: (by_id[i].order, i)):
                indegree[child_id] -= 1
                if indegree[child_id] == 0:
                    ready.append(by_id[child_id])
        if len(ordered) != len(agents):
            logger.error("Cycle detected in agent dependencies; falling back to configured order.")
            return sorted(agents, key=lambda a: (a.order, a.id))
        return ordered

    def _dependency_context(self, depends_on: list[str], outputs: dict[str, dict], artifacts: list[dict]) -> str:
        if not depends_on:
            return ""
        chunks = []
        for dep in depends_on:
            output = outputs.get(dep)
            if output:
                chunks.append(f"## Agent: {output.get('display_name', dep)}\n{output.get('markdown', '')}")
            dep_artifacts = [a for a in artifacts if a.get("agent_id") == dep]
            for artifact in dep_artifacts:
                chunks.append(
                    f"## Artifact: {artifact.get('title')}\n"
                    f"type: {artifact.get('type')}\n"
                    f"status: {artifact.get('status')}\n"
                    f"sid: {artifact.get('sid')}\n"
                    f"rows: {len(artifact.get('rows', []))}"
                )
        return "\n\n".join(chunks)

    def _run_agent_tools(self, cfg, request: dict, output: dict) -> list[dict]:
        if "splunk_search" not in cfg.skills:
            logger.debug("Agent %s: skipping tools (skills=%r).", cfg.id, cfg.skills)
            return []
        if output.get("status") == "error":
            logger.debug("Agent %s: skipping tools (agent returned error).", cfg.id)
            return []
        earliest = request.get("time_range") or "-24h"
        blocks = extract_spl_blocks(output.get("markdown", ""))
        if not blocks:
            logger.warning("Agent %s has splunk_search skill but no ```spl blocks found in output.", cfg.id)
            return []
        logger.info("Agent %s: executing %d SPL search(es).", cfg.id, len(blocks[:4]))
        artifacts = []
        for block in blocks[:4]:
            artifacts.append(
                run_splunk_search_artifact(
                    agent_id=cfg.id,
                    title=block["title"],
                    spl=block["spl"],
                    earliest=earliest,
                    latest="now",
                    client_factory=self.splunk_client_factory,
                    viz_hint=block.get("viz_hint"),
                )
            )
        return artifacts
