"""Shared investigation result helpers.

The API still returns plain dictionaries so FastAPI can serialize without
custom encoders, but these helpers keep the wire shape consistent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def markdown_section(section_id: str, title: str, markdown: str, agent_id: str | None = None) -> dict:
    return {
        "id": section_id,
        "type": "markdown",
        "title": title,
        "agent_id": agent_id,
        "markdown": markdown,
    }


def audit_event(
    event_type: str,
    investigation_id: str,
    username: str,
    status: str = "ok",
    **details: Any,
) -> dict:
    return {
        "type": event_type,
        "investigation_id": investigation_id,
        "username": username,
        "status": status,
        "timestamp": now_iso(),
        "details": details,
    }


def public_artifact(artifact: dict) -> dict:
    """Return the browser-safe artifact shape.

    Real Splunk rows are fetched by the browser through Splunk Web's authenticated
    proxy. Demo artifacts retain rows because they have no Splunk search job.
    """
    if artifact.get("type") != "splunk_search" or artifact.get("sid") == "demo":
        return dict(artifact)
    return {
        **artifact,
        "fields": [],
        "rows": [],
        "messages": [],
    }


def public_investigation(job: dict) -> dict:
    """Return a shallow browser-safe projection of an investigation."""
    return {
        **job,
        "artifacts": [public_artifact(artifact) for artifact in job.get("artifacts", [])],
    }
