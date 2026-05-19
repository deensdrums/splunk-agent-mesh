"""Timeline Agent — correlates raw events into a chronological timeline."""

import logging

logger = logging.getLogger(__name__)

SOURCE_MAP = {
    "endpoint": "endpoint",
    "dns": "dns",
    "wineventlog": "auth",
    "proxy": "proxy",
    "firewall": "firewall",
}

SEVERITY_RULES = [
    (lambda e: "bytes_out" in e and int(e.get("bytes_out", 0)) > 10_000_000, "critical"),
    (lambda e: "zip" in str(e.get("target_filename", "")).lower(), "high"),
    (lambda e: e.get("process_name", "") == "powershell.exe", "high"),
    (lambda e: e.get("record_type") == "A" and int(e.get("first_seen_domain_days", 999)) < 30, "high"),
    (lambda e: e.get("event_id") == 4624, "medium"),
]


def classify_severity(event: dict) -> str:
    for rule, severity in SEVERITY_RULES:
        try:
            if rule(event):
                return severity
        except Exception:
            pass
    return "low"


def event_to_timeline_entry(event: dict) -> dict:
    source_raw = event.get("index", event.get("source", "unknown")).split(":")[0]
    source = SOURCE_MAP.get(source_raw, source_raw)
    severity = classify_severity(event)

    process = event.get("process_name", "")
    parent = event.get("parent_process_name", "")
    cmd = event.get("command_line", "")
    query = event.get("query", "")
    dest = event.get("dest_host", event.get("dest_ip", ""))
    filename = event.get("target_filename", "")
    bytes_out = event.get("bytes_out", "")

    if process and parent:
        title = f"{parent} spawned {process}"
        desc = cmd[:120] if cmd else f"{parent} → {process}"
    elif query:
        title = f"DNS query: {query}"
        desc = f"Resolved to {event.get('answer', 'unknown')}"
    elif dest and event.get("event_id") == 4624:
        title = f"Authentication to {dest}"
        desc = f"User {event.get('user', '?')} logged on to {dest}"
    elif filename:
        title = f"File created: {filename}"
        desc = f"Archive or file created by {event.get('user', '?')}"
    elif bytes_out:
        title = "Large outbound network transfer"
        desc = f"{int(bytes_out):,} bytes sent to {dest}"
    else:
        title = "Security event"
        desc = str(event)[:100]

    return {
        "time": event.get("_time", ""),
        "title": title,
        "description": desc,
        "source": source,
        "severity": severity,
    }


class TimelineAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def run(self, ctx: dict) -> dict:
        events = ctx.get("events", [])
        timeline = sorted(
            [event_to_timeline_entry(e) for e in events],
            key=lambda x: x["time"],
        )
        logger.info("TimelineAgent: built %d timeline entries.", len(timeline))
        return {"timeline": timeline}
