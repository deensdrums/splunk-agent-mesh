"""Detection Gap Agent — generates a reusable Splunk detection rule."""

import logging

logger = logging.getLogger(__name__)

DETECTION_TEMPLATES = {
    "encoded_powershell": {
        "title": "Office-spawned encoded PowerShell",
        "spl": (
            'index=endpoint process_name=powershell.exe '
            '(command_line="*-enc*" OR command_line="*EncodedCommand*") '
            '(parent_process_name=winword.exe OR parent_process_name=excel.exe OR parent_process_name=outlook.exe) '
            '| stats count min(_time) as first_seen max(_time) as last_seen by host user parent_process_name command_line'
        ),
        "description": "Detects suspicious Office child process behavior commonly associated with phishing payload execution.",
        "severity": "high",
        "mitre": ["T1059.001", "T1027"],
    },
    "large_outbound": {
        "title": "Unusually large outbound transfer",
        "spl": (
            'index=proxy bytes_out > 10000000 '
            '| stats sum(bytes_out) as total_bytes count by host user dest_ip '
            '| where total_bytes > 50000000 '
            '| sort -total_bytes'
        ),
        "description": "Detects hosts sending more than 50 MB to a single external destination.",
        "severity": "high",
        "mitre": ["T1041"],
    },
}


class DetectionGapAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def run(self, ctx: dict) -> dict:
        events = ctx.get("events", [])

        has_powershell = any(
            e.get("process_name") == "powershell.exe" and "enc" in str(e.get("command_line", "")).lower()
            for e in events
        )
        has_large_outbound = any(int(e.get("bytes_out", 0)) > 10_000_000 for e in events)

        if has_powershell:
            detection = DETECTION_TEMPLATES["encoded_powershell"]
        elif has_large_outbound:
            detection = DETECTION_TEMPLATES["large_outbound"]
        else:
            detection = {
                "title": "Generic suspicious activity",
                "spl": "index=* | head 10",
                "description": "No specific detection pattern identified. Review evidence manually.",
                "severity": "low",
                "mitre": [],
            }

        logger.info("DetectionGapAgent: generated detection '%s'.", detection["title"])
        return {"detection_recommendation": detection}
