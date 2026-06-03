"""Deterministic demo: a replayable Log4Shell investigation.

Demo mode makes **no** LLM or Splunk call. This module is the *authoritative*
source for the canned investigation — the frontend has no duplicate fixture.

When a ``progress_callback`` is supplied (the async ``/start`` + SSE path), the
events and the search artifacts are **replayed with pacing**: narration appears,
a search card goes pending → running → done, then findings, a handoff, and a
final answer — so it looks like a live agentic run. Without a callback (the
synchronous ``/run`` path) the final result is assembled instantly.

Pacing is controlled by ``AGENT_MESH_DEMO_STEP_SECONDS`` (default 1.1; tests set
0 for speed).
"""

from __future__ import annotations

import os
import time
from typing import Callable

from ..agents.agent_config import AgentConfig
from ..investigation_models import now_iso

_DEMO_TS = "2026-06-02T14:00:00+00:00"
_FALLBACK_ID = "spl_hunter"
_FALLBACK_DISPLAY = "Threat Hunter"
_FALLBACK_MODEL = "claude-haiku-4-5-20251001"  # cosmetic; demo makes no call


def _step_delay() -> float:
    try:
        return max(0.0, float(os.getenv("AGENT_MESH_DEMO_STEP_SECONDS", "1.1")))
    except ValueError:
        return 1.1


# ---- Scenario: Log4Shell exploitation of public web servers -> C2 ----------

_TIMECHART_ROWS = [
    {"_time": "2026-06-02T13:47:00+00:00", "count": "4"},
    {"_time": "2026-06-02T13:48:00+00:00", "count": "21"},
    {"_time": "2026-06-02T13:49:00+00:00", "count": "17"},
    {"_time": "2026-06-02T13:50:00+00:00", "count": "9"},
    {"_time": "2026-06-02T13:51:00+00:00", "count": "3"},
]

_CALLBACK_ROWS = [
    {"_time": "2026-06-02T13:50:12+00:00", "src_ip": "web-prod-04", "dest_ip": "185.220.101.47",
     "dest_port": "1389", "action": "allowed"},
    {"_time": "2026-06-02T13:50:41+00:00", "src_ip": "web-prod-07", "dest_ip": "185.220.101.47",
     "dest_port": "1389", "action": "allowed"},
]

# Artifact specs, in the order their splunk_search events appear. Each becomes a
# pending -> running -> done artifact during replay (stable id across states).
def _artifact_specs(agent_id: str) -> list[dict]:
    return [
        {
            "id": "artifact-demo-jndi",
            "agent_id": agent_id,
            "title": "JNDI exploit attempts in web access logs",
            "spl": ('index=web sourcetype=access_combined ("${jndi:" OR "jndi:ldap")\n'
                    "| timechart span=1m count"),
            "fields": ["_time", "count"],
            "rows": _TIMECHART_ROWS,
            "kind": "timechart",
            "reason": "SPL uses timechart.",
        },
        {
            "id": "artifact-demo-callback",
            "agent_id": agent_id,
            "title": "Outbound LDAP/RMI callbacks from web servers",
            "spl": ("index=firewall src_ip IN (web-prod-04, web-prod-07) "
                    "dest_port IN (389, 636, 1099, 1389)\n"
                    "| table _time src_ip dest_ip dest_port action | sort - _time"),
            "fields": ["_time", "src_ip", "dest_ip", "dest_port", "action"],
            "rows": _CALLBACK_ROWS,
            "kind": "table",
            "reason": "Agent-specified visualization hint.",
        },
    ]


def _scenario_events() -> list[dict]:
    return [
        {
            "type": "narration",
            "title": "Starting investigation",
            "text": ("An IDS alert flagged JNDI lookup strings against our public web tier. "
                     "I'll confirm whether this is Log4Shell exploitation and whether any host "
                     "actually called back out."),
            "payload": {},
        },
        {
            "type": "splunk_search",
            "title": "JNDI exploit attempts in web access logs",
            "text": "Looking for ${jndi:ldap...} payloads against the public web servers.",
            "payload": {
                "query": ('index=web sourcetype=access_combined ("${jndi:" OR "jndi:ldap") '
                          "| timechart span=1m count"),
                "purpose": "Confirm and time-bound Log4Shell exploitation attempts.",
                "type": "timechart",
            },
        },
        {
            "type": "result_summary",
            "title": "Exploit burst confirmed",
            "text": ("54 JNDI exploit attempts in a ~5-minute burst (peak 13:48), targeting "
                     "web-prod-04 and web-prod-07 from 45.137.21.53."),
            "payload": {},
        },
        {
            "type": "finding",
            "title": "Log4Shell exploitation attempt",
            "text": ("Inbound ${jndi:ldap} payloads match CVE-2021-44228 (Log4Shell) against the "
                     "public web tier."),
            "payload": {
                "cve": "CVE-2021-44228",
                "technique": "T1190",
                "hosts": "web-prod-04, web-prod-07",
                "src_ip": "45.137.21.53",
                "confidence": "high",
            },
        },
        {
            "type": "splunk_search",
            "title": "Outbound LDAP/RMI callbacks from web servers",
            "text": ("Checking whether the targeted servers made the outbound LDAP/RMI callback "
                     "that confirms successful exploitation."),
            "payload": {
                "query": ("index=firewall src_ip IN (web-prod-04, web-prod-07) "
                          "dest_port IN (389, 636, 1099, 1389) "
                          "| table _time src_ip dest_ip dest_port action | sort - _time"),
                "purpose": "Distinguish a blocked probe from real code execution + C2.",
                "type": "table",
            },
        },
        {
            "type": "finding",
            "title": "Confirmed C2 callback",
            "text": ("web-prod-04 and web-prod-07 both made outbound LDAP connections to "
                     "185.220.101.47:1389 — successful exploitation, not just a probe."),
            "payload": {
                "c2": "185.220.101.47:1389",
                "technique": "T1105",
                "hosts": "web-prod-04, web-prod-07",
                "confidence": "high",
            },
        },
        {
            "type": "handoff",
            "title": "Reporting agent requested",
            "text": "Asking the reporting agent to turn these findings into a leadership brief.",
            "payload": {"sub_agent": "executive_brief", "task": "summarize_findings"},
        },
        {
            "type": "result_summary",
            "title": "Report drafted",
            "text": ("The reporting agent rated this Critical (confidence 0.9), mapped it to "
                     "T1190 and T1105, and recommended emergency Log4j remediation and host isolation."),
            "payload": {},
        },
        {
            "type": "final",
            "title": "Investigation complete",
            "text": ("Confirmed active Log4Shell (CVE-2021-44228) exploitation of web-prod-04 and "
                     "web-prod-07 with outbound C2 to 185.220.101.47. Treat both hosts as compromised."),
            "payload": {
                "summary": "Active Log4Shell exploitation with confirmed C2 on two public web servers.",
                "recommended_actions": [
                    "Isolate web-prod-04 and web-prod-07 from the network",
                    "Block 185.220.101.47 at the perimeter",
                    "Patch/upgrade Log4j to 2.17.1+ (or set log4j2.formatMsgNoLookups=true)",
                    "Hunt for web shells and persistence on both hosts",
                    "Rotate any credentials or secrets reachable from those hosts",
                ],
            },
        },
    ]


# ---- shape helpers ---------------------------------------------------------

def _events_md(events: list[dict]) -> str:
    parts = []
    for e in events:
        title, text = e.get("title", ""), e.get("text", "")
        parts.append(f"**{title}**\n\n{text}" if title else text)
    return "\n\n".join(p for p in parts if p)


def _artifact(spec: dict, status: str, revision: int, rows: list[dict]) -> dict:
    return {
        "id": spec["id"],
        "type": "splunk_search",
        "agent_id": spec["agent_id"],
        "title": spec["title"],
        "spl": spec["spl"],
        "earliest": "-24h",
        "latest": "now",
        "sid": "demo",  # sid "demo" => API keeps rows; browser does not poll Splunk Web
        "status": status,
        "fields": spec["fields"] if status == "done" else [],
        "rows": rows,
        "messages": [],
        "error": None,
        "started_at": _DEMO_TS,
        "completed_at": _DEMO_TS if status in ("done", "error") else None,
        "visualization": {"kind": spec["kind"], "reason": spec["reason"]},
        "_revision": revision,
    }


def _output(agent_id: str, display: str, model: str, events: list[dict], status: str,
            iteration: int, started: str, phase: str | None, artifact_ids: list[str] | None = None) -> dict:
    out = {
        "agent_id": agent_id,
        "display_name": display,
        "status": status,
        "events": list(events),
        "markdown": _events_md(events),
        "model": model,
        "started_at": started,
        "completed_at": now_iso() if status == "completed" else None,
        "error": None,
        "phase": phase,
        "_iteration": iteration,
    }
    if artifact_ids is not None:
        out["artifacts"] = artifact_ids
    return out


def _result(investigation_id: str, owner: str, agent_id: str, output: dict,
            artifacts: list[dict], started: str) -> dict:
    return {
        "id": investigation_id,
        "owner": owner,
        "status": "complete",
        "started_at": started,
        "completed_at": now_iso(),
        "agent_order": [agent_id],
        "agents": {agent_id: output},
        "sections": [],
        "artifacts": artifacts,
        "audit": [],
    }


# ---- public entry point ----------------------------------------------------

def build_demo_result(
    agents: list[AgentConfig],
    investigation_id: str = "demo-investigation-001",
    owner: str = "demo-user",
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """Build (or replay) the deterministic demo investigation.

    With ``progress_callback`` the events + artifacts are streamed with pacing
    (the live-looking path); without it the final result is assembled instantly.
    Either way the returned dict is the final investigation result.
    """
    agent_id = agents[0].id if agents else _FALLBACK_ID
    display = agents[0].display_name if agents else _FALLBACK_DISPLAY
    model = agents[0].model if agents else _FALLBACK_MODEL
    started = now_iso()
    events = _scenario_events()
    specs = _artifact_specs(agent_id)

    if progress_callback is None:
        artifacts = [_artifact(s, "done", 1, s["rows"]) for s in specs]
        output = _output(agent_id, display, model, events, "completed", len(events) + 1,
                         started, None, [s["id"] for s in specs])
        return _result(investigation_id, owner, agent_id, output, artifacts, started)

    # Paced replay through the SSE/job path.
    shown: list[dict] = []
    artifacts_done: list[dict] = []
    iteration = 0
    search_i = 0
    saw_handoff = False

    def emit(changed: dict | None, status: str, phase: str | None) -> None:
        nonlocal iteration
        iteration += 1
        progress_callback({
            "agent_order": [agent_id],
            "agents": {agent_id: _output(agent_id, display, model, shown, status, iteration, started, phase)},
            "artifacts": [changed] if changed else [],
            "sections": [],
            "audit": [],
        })

    for ev in events:
        shown.append(ev)
        if ev["type"] == "splunk_search":
            spec = specs[search_i]
            search_i += 1
            emit(_artifact(spec, "pending", 1, []), "iterating", None)
            time.sleep(_step_delay())
            half = max(1, len(spec["rows"]) // 2)
            emit(_artifact(spec, "running", 2, spec["rows"][:half]), "iterating", None)
            time.sleep(_step_delay())
            done = _artifact(spec, "done", 3, spec["rows"])
            artifacts_done.append(done)
            emit(done, "iterating", "interpreting")
            time.sleep(_step_delay())
        else:
            if ev["type"] == "handoff":
                saw_handoff = True
                phase = "delegating"
            elif ev["type"] == "result_summary" and saw_handoff:
                phase = "finalizing"
            else:
                phase = None
            emit(None, "iterating", phase)
            time.sleep(_step_delay())

    output = _output(agent_id, display, model, events, "completed", iteration + 1, started, None,
                     [s["id"] for s in specs])
    return _result(investigation_id, owner, agent_id, output, artifacts_done, started)
