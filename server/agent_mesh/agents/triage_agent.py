"""Triage Agent — extracts entities and classifies initial severity."""

import re
import logging

logger = logging.getLogger(__name__)


class TriageAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def run(self, ctx: dict) -> dict:
        req = ctx.get("request", {})
        description = req.get("description", "")
        host = req.get("host") or self._extract_host(description)
        user = req.get("user") or self._extract_user(description)

        entities = {
            "users": [user] if user else [],
            "hosts": [host] if host else [],
            "domains": self._extract_domains(description),
            "ips": self._extract_ips(description),
            "files": [],
        }

        severity = self._classify_severity(description)
        logger.info("TriageAgent: entities=%s severity=%s", entities, severity)

        return {
            "entities": entities,
            "severity": severity,
            "triage_notes": f"Extracted entities from description. Initial severity: {severity}.",
        }

    def _extract_host(self, text: str) -> str | None:
        m = re.search(r'\b([A-Z][A-Z0-9\-]{2,20})\b', text)
        return m.group(1) if m else None

    def _extract_user(self, text: str) -> str | None:
        m = re.search(r'\b([a-z][a-z0-9]{2,15})\b', text)
        return m.group(1) if m else None

    def _extract_domains(self, text: str) -> list[str]:
        return re.findall(r'\b[a-z0-9\-]+\.[a-z]{2,}\b', text.lower())

    def _extract_ips(self, text: str) -> list[str]:
        return re.findall(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', text)

    def _classify_severity(self, text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ['exfil', 'ransomware', 'lateral', 'critical']):
            return 'Critical'
        if any(w in lower for w in ['powershell', 'encoded', 'obfusc', 'malware', 'c2', 'beacon']):
            return 'High'
        if any(w in lower for w in ['suspicious', 'unusual', 'anomal']):
            return 'Medium'
        return 'Low'
