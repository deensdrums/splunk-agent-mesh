"""Response Agent — generates a prioritized, human-approved response plan."""

import logging

logger = logging.getLogger(__name__)


class ResponseAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def run(self, ctx: dict) -> dict:
        entities = ctx.get("entities", {})
        severity = ctx.get("severity", "Medium")

        plan = []

        hosts = entities.get("hosts", [])
        users = entities.get("users", [])
        domains = entities.get("domains", [])

        if hosts:
            plan.append({
                "action": "Isolate host",
                "target": hosts[0],
                "risk": "May interrupt user productivity.",
                "requires_approval": True,
            })

        if users:
            plan.append({
                "action": "Disable active sessions",
                "target": users[0],
                "risk": "May interrupt legitimate access.",
                "requires_approval": True,
            })

        if domains:
            plan.append({
                "action": "Block domain",
                "target": domains[0],
                "risk": "Low if domain is confirmed malicious or rare.",
                "requires_approval": True,
            })

        plan.append({
            "action": "Hunt across environment",
            "target": "All hosts",
            "risk": "Read-only search.",
            "requires_approval": False,
        })

        if severity in ("High", "Critical"):
            plan.append({
                "action": "Preserve forensic evidence",
                "target": hosts[0] if hosts else "affected systems",
                "risk": "None — preservation only.",
                "requires_approval": False,
            })

        logger.info("ResponseAgent: generated %d actions.", len(plan))
        return {"response_plan": plan}
