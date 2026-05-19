"""Agent orchestrator. Runs agents sequentially and aggregates results."""

import logging
from ..demo.demo_case import DEMO_RESULT
from .triage_agent import TriageAgent
from .spl_hunter_agent import SPLHunterAgent
from .timeline_agent import TimelineAgent
from .blast_radius_agent import BlastRadiusAgent
from .detection_gap_agent import DetectionGapAgent
from .response_agent import ResponseAgent
from .executive_brief_agent import ExecutiveBriefAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, llm_provider=None, splunk_client=None):
        self.llm = llm_provider
        self.splunk = splunk_client

    def run(self, request: dict) -> dict:
        if request.get("demo"):
            logger.info("Demo mode: returning static result.")
            return DEMO_RESULT

        errors: list[str] = []
        context: dict = {"request": request, "events": [], "timeline": [], "entities": {}}

        agents = [
            TriageAgent(self.llm),
            SPLHunterAgent(self.llm, self.splunk),
            TimelineAgent(self.llm),
            BlastRadiusAgent(self.llm, self.splunk),
            DetectionGapAgent(self.llm),
            ResponseAgent(self.llm),
            ExecutiveBriefAgent(self.llm),
        ]

        for agent in agents:
            try:
                result = agent.run(context)
                context.update(result)
            except Exception as e:
                error_msg = f"{agent.__class__.__name__} failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        return self._build_result(context, errors)

    def _build_result(self, ctx: dict, errors: list[str]) -> dict:
        return {
            "id": ctx.get("investigation_id", "inv-001"),
            "status": "complete",
            "title": ctx.get("title", "Investigation Complete"),
            "severity": ctx.get("severity", "Unknown"),
            "confidence": ctx.get("confidence", 0.0),
            "summary": ctx.get("summary", "Investigation complete. See evidence for details."),
            "affected_entities": ctx.get("entities", {}),
            "mitre": ctx.get("mitre", []),
            "timeline": ctx.get("timeline", []),
            "evidence": ctx.get("evidence", []),
            "response_plan": ctx.get("response_plan", []),
            "detection_recommendation": ctx.get(
                "detection_recommendation",
                {"title": "No detection generated", "spl": "", "description": "", "severity": "low", "mitre": []},
            ),
            "agent_errors": errors,
        }
