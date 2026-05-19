"""Executive Brief Agent — synthesizes findings into the final report."""

import logging

logger = logging.getLogger(__name__)

MITRE_MAP = {
    ("powershell.exe", "enc"): ("T1059.001", "PowerShell", 0.92),
    ("powershell.exe", "encoded"): ("T1059.001", "PowerShell", 0.92),
    ("dns", "rare"): ("T1105", "Ingress Tool Transfer", 0.76),
    ("zip", "archive"): ("T1560.001", "Archive Collected Data", 0.80),
    ("bytes_out", "large"): ("T1041", "Exfiltration Over C2 Channel", 0.83),
}


class ExecutiveBriefAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def run(self, ctx: dict) -> dict:
        events = ctx.get("events", [])
        severity = ctx.get("severity", "Medium")
        entities = ctx.get("entities", {})
        timeline = ctx.get("timeline", [])

        mitre = self._detect_mitre(events)
        confidence = self._compute_confidence(events, mitre)
        summary = self._build_summary(entities, timeline, severity)

        logger.info("ExecutiveBriefAgent: %d MITRE techniques, confidence=%.2f.", len(mitre), confidence)
        return {
            "mitre": mitre,
            "confidence": confidence,
            "summary": summary,
            "title": self._build_title(entities),
            "evidence": self._build_evidence(events),
        }

    def _detect_mitre(self, events: list[dict]) -> list[dict]:
        techniques: list[dict] = []
        for event in events:
            cmd = str(event.get("command_line", "")).lower()
            proc = event.get("process_name", "").lower()
            source = event.get("index", "").lower()
            fname = str(event.get("target_filename", "")).lower()
            bytes_out = int(event.get("bytes_out", 0))

            if proc == "powershell.exe" and ("-enc" in cmd or "encodedcommand" in cmd):
                techniques.append({
                    "technique_id": "T1059.001",
                    "name": "PowerShell",
                    "confidence": 0.92,
                    "evidence": "powershell.exe with encoded command observed",
                })
                techniques.append({
                    "technique_id": "T1027",
                    "name": "Obfuscated Files or Information",
                    "confidence": 0.81,
                    "evidence": "-enc or -EncodedCommand in command line",
                })
            if source == "dns" and int(event.get("first_seen_domain_days", 999)) < 30:
                techniques.append({
                    "technique_id": "T1105",
                    "name": "Ingress Tool Transfer",
                    "confidence": 0.76,
                    "evidence": "Rare domain contacted post-execution",
                })
            if ".zip" in fname or ".rar" in fname:
                techniques.append({
                    "technique_id": "T1560.001",
                    "name": "Archive Collected Data",
                    "confidence": 0.80,
                    "evidence": f"Archive file created: {event.get('target_filename')}",
                })
            if bytes_out > 10_000_000:
                techniques.append({
                    "technique_id": "T1041",
                    "name": "Exfiltration Over C2 Channel",
                    "confidence": 0.83,
                    "evidence": f"{bytes_out:,} bytes sent to external IP",
                })

        seen = set()
        deduped = []
        for t in techniques:
            if t["technique_id"] not in seen:
                seen.add(t["technique_id"])
                deduped.append(t)
        return deduped

    def _compute_confidence(self, events: list[dict], mitre: list[dict]) -> float:
        if not events:
            return 0.0
        base = min(len(events) / 10, 0.7)
        mitre_bonus = min(len(mitre) * 0.05, 0.25)
        return round(base + mitre_bonus, 2)

    def _build_summary(self, entities: dict, timeline: list[dict], severity: str) -> str:
        hosts = entities.get("hosts", [])
        users = entities.get("users", [])
        n_events = len(timeline)
        return (
            f"Investigation identified {n_events} correlated events across "
            f"{', '.join(hosts) if hosts else 'unknown hosts'}. "
            f"Affected user: {', '.join(users) if users else 'unknown'}. "
            f"Severity: {severity}."
        )

    def _build_title(self, entities: dict) -> str:
        hosts = entities.get("hosts", [])
        return f"Investigation: {hosts[0]}" if hosts else "Security Investigation"

    def _build_evidence(self, events: list[dict]) -> list[dict]:
        evidence = []
        for e in events[:10]:
            source = e.get("index", e.get("source", "unknown")).split(":")[0]
            field, value, interp = self._key_field(e)
            evidence.append({
                "source": source,
                "time": e.get("_time", ""),
                "host": e.get("host", ""),
                "user": e.get("user", ""),
                "field": field,
                "value": value,
                "interpretation": interp,
            })
        return evidence

    def _key_field(self, event: dict) -> tuple[str, str, str]:
        if event.get("command_line"):
            return "command_line", str(event["command_line"])[:100], "Command line from process event."
        if event.get("query"):
            return "query", str(event["query"]), "DNS query observed."
        if event.get("bytes_out"):
            return "bytes_out", str(event["bytes_out"]), "Outbound data volume."
        if event.get("dest_host"):
            return "dest_host", str(event["dest_host"]), "Authentication destination."
        return "raw", str(event)[:80], "Raw event."
