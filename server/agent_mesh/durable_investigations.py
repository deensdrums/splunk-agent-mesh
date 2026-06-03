"""Durable investigation persistence for Splunk KV Store.

The in-memory job store remains the execution cache. This module provides the
durable snapshot contract and a Splunk KV Store repository used for checkpointing
and later restoration.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from .config import SPLUNK_APP_ID, SPLUNK_HOST
from .investigation_models import now_iso
from .request_context import RequestContext

logger = logging.getLogger(__name__)

COLLECTION_NAME = "agent_mesh_investigations"
SCHEMA_VERSION = 1
RETENTION_DAYS = 30
WRITE_TIMEOUT_SECONDS = 2.0
READ_TIMEOUT_SECONDS = 5.0

TERMINAL_STATUSES = {"complete", "error", "failed", "cancelled", "timed_out"}


class DurableInvestigationError(RuntimeError):
    """Raised when durable persistence cannot complete."""


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _plus_days(value: str | None, days: int) -> str:
    base = _parse_iso(value) or datetime.now(timezone.utc)
    return (base + timedelta(days=days)).isoformat(timespec="seconds")


def _durable_status(status: str | None) -> str:
    if status == "error":
        return "failed"
    if status in {"pending", "running", "complete", "failed", "cancelled", "timed_out"}:
        return status
    return status or "running"


def _api_status(status: str | None) -> str:
    if status == "failed":
        return "error"
    return status or "running"


def _artifact_revision(artifact: dict) -> int:
    value = artifact.get("_revision", artifact.get("revision", 0))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _artifact_metadata(artifact: dict) -> dict:
    metadata = copy.deepcopy(artifact)
    metadata.pop("rows", None)
    metadata.pop("messages", None)
    metadata["revision"] = _artifact_revision(artifact)
    metadata.pop("_revision", None)
    return metadata


def _event_entries(job: dict) -> list[dict]:
    entries: list[dict] = []
    sequence = 0
    artifacts_by_agent: dict[str, list[dict]] = {}
    for artifact in job.get("artifacts", []):
        artifacts_by_agent.setdefault(artifact.get("agent_id", ""), []).append(artifact)

    search_indexes: dict[str, int] = {}
    for agent_id in job.get("agent_order", []) or job.get("agents", {}).keys():
        output = job.get("agents", {}).get(agent_id, {})
        for event in output.get("events", []) or []:
            sequence += 1
            entry = {
                "sequence": sequence,
                "agent_id": agent_id,
                "emitted_at": output.get("completed_at") or output.get("started_at") or job.get("updated_at") or now_iso(),
                "event": copy.deepcopy(event),
            }
            if event.get("type") == "splunk_search":
                index = search_indexes.get(agent_id, 0)
                agent_artifacts = artifacts_by_agent.get(agent_id, [])
                if index < len(agent_artifacts):
                    entry["artifact_id"] = agent_artifacts[index].get("id")
                search_indexes[agent_id] = index + 1
            entries.append(entry)
    return entries


def investigation_record(job: dict, request_payload: dict | None = None, context: RequestContext | None = None) -> dict:
    """Build the durable STATE-001 record from the current job snapshot."""
    started_at = job.get("started_at") or now_iso()
    completed_at = job.get("completed_at")
    events = _event_entries(job)
    artifacts = [_artifact_metadata(artifact) for artifact in job.get("artifacts", [])]
    agent_order = job.get("agent_order", [])
    agents = copy.deepcopy(job.get("agents", {}))
    active_agent_id = agent_order[0] if agent_order else next(iter(agents), None)
    final_summary = None
    for entry in reversed(events):
        event = entry.get("event", {})
        if event.get("type") == "final":
            final_summary = event.get("payload", {}).get("summary") or event.get("text")
            break

    owner = job.get("owner") or (context.username if context else "dev-user")
    record_revision = int(job.get("_durable_revision", 0)) + 1
    return {
        "_key": job["id"],
        "schema_version": SCHEMA_VERSION,
        "investigation_id": job["id"],
        "owner": {
            "username": owner,
            "display_name": None,
            "auth_source": context.source if context else "unknown",
        },
        "created_at": started_at,
        "updated_at": now_iso(),
        "started_at": started_at,
        "completed_at": completed_at,
        "expires_at": job.get("expires_at") or _plus_days(started_at, RETENTION_DAYS),
        "status": _durable_status(job.get("status")),
        "status_reason": job.get("error"),
        "last_sequence": len(events),
        "record_revision": record_revision,
        "request": copy.deepcopy(request_payload or job.get("request") or {}),
        "summary": {
            "title": _summary_title(request_payload or job.get("request") or {}, events),
            "first_event_title": events[0]["event"].get("title") if events else None,
            "final_summary": final_summary,
            "event_count": len(events),
            "artifact_count": len(artifacts),
            "active_agent_id": active_agent_id,
        },
        "agent_order": copy.deepcopy(agent_order),
        "agents": {
            agent_id: _agent_metadata(agent)
            for agent_id, agent in agents.items()
        },
        "events": events,
        "artifacts": artifacts,
        "audit": _audit_entries(job.get("audit", [])),
    }


def _summary_title(request_payload: dict, events: list[dict]) -> str | None:
    alert = request_payload.get("alert_name")
    if alert:
        return alert
    if events:
        return events[0]["event"].get("title")
    description = request_payload.get("description", "")
    return description[:80] or None


def _agent_metadata(agent: dict) -> dict:
    return {
        "agent_id": agent.get("agent_id"),
        "display_name": agent.get("display_name"),
        "status": agent.get("status"),
        "phase": agent.get("phase"),
        "started_at": agent.get("started_at"),
        "completed_at": agent.get("completed_at"),
        "error": agent.get("error"),
        "model": agent.get("model"),
        "iteration": agent.get("_iteration"),
    }


def _audit_entries(audit: list[dict]) -> list[dict]:
    entries = []
    for index, item in enumerate(audit, start=1):
        entries.append({
            "sequence": index,
            "at": item.get("timestamp") or now_iso(),
            "type": item.get("type"),
            "actor": item.get("username"),
            "detail": copy.deepcopy(item.get("details", {})),
        })
    return entries


def job_from_record(record: dict) -> dict:
    """Project a durable record back into the public investigation shape."""
    agents: dict[str, dict] = {}
    events_by_agent: dict[str, list[dict]] = {}
    for entry in record.get("events", []):
        events_by_agent.setdefault(entry.get("agent_id", ""), []).append(copy.deepcopy(entry.get("event", {})))

    for agent_id, metadata in record.get("agents", {}).items():
        agents[agent_id] = {
            "agent_id": metadata.get("agent_id") or agent_id,
            "display_name": metadata.get("display_name") or agent_id,
            "status": metadata.get("status"),
            "phase": metadata.get("phase"),
            "events": events_by_agent.get(agent_id, []),
            "markdown": "",
            "model": metadata.get("model"),
            "started_at": metadata.get("started_at"),
            "completed_at": metadata.get("completed_at"),
            "error": metadata.get("error"),
            "_iteration": metadata.get("iteration", 0),
        }

    artifacts = []
    for artifact in record.get("artifacts", []):
        restored = copy.deepcopy(artifact)
        revision = restored.pop("revision", 0)
        restored["_revision"] = revision
        restored.setdefault("rows", [])
        restored.setdefault("messages", [])
        artifacts.append(restored)

    return {
        "id": record.get("investigation_id") or record.get("_key"),
        "owner": record.get("owner", {}).get("username"),
        "status": _api_status(record.get("status")),
        "started_at": record.get("started_at"),
        "completed_at": record.get("completed_at"),
        "agent_order": record.get("agent_order", []),
        "agents": agents,
        "sections": [],
        "artifacts": artifacts,
        "audit": record.get("audit", []),
        "error": record.get("status_reason"),
    }


class SplunkKVInvestigationRepository:
    """KV Store repository using the caller's Splunk session token."""

    def __init__(
        self,
        splunk_host: str,
        token: str,
        app_id: str = SPLUNK_APP_ID,
        auth_scheme: str = "Splunk",
        verify: bool = False,
    ):
        self.splunk_host = splunk_host.rstrip("/")
        self.token = token
        self.app_id = app_id
        self.auth_scheme = auth_scheme
        self.verify = verify

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"{self.auth_scheme} {self.token}"}

    def upsert(self, record: dict) -> None:
        key = quote(record["_key"], safe="")
        url = self._collection_url(key)
        payload = copy.deepcopy(record)
        response = httpx.post(
            url,
            params={"output_mode": "json"},
            headers=self._headers,
            json=payload,
            verify=self.verify,
            timeout=WRITE_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            response = httpx.post(
                self._collection_url(),
                params={"output_mode": "json"},
                headers=self._headers,
                json=payload,
                verify=self.verify,
                timeout=WRITE_TIMEOUT_SECONDS,
            )
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DurableInvestigationError(f"KV Store upsert failed: {exc}") from exc

    def get(self, investigation_id: str, username: str | None = None) -> dict | None:
        key = quote(investigation_id, safe="")
        response = httpx.get(
            self._collection_url(key),
            params={"output_mode": "json"},
            headers=self._headers,
            verify=self.verify,
            timeout=READ_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return None
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DurableInvestigationError(f"KV Store read failed: {exc}") from exc
        record = response.json()
        if username and record.get("owner", {}).get("username") != username:
            return None
        if _is_expired(record):
            return None
        return record

    def _collection_url(self, key: str | None = None) -> str:
        path = f"/servicesNS/nobody/{self.app_id}/storage/collections/data/{COLLECTION_NAME}"
        if key:
            path = f"{path}/{key}"
        return f"{self.splunk_host}{path}"


class NullInvestigationRepository:
    def upsert(self, _record: dict) -> None:
        return None

    def get(self, _investigation_id: str, username: str | None = None) -> dict | None:
        return None


def repository_from_context(context: RequestContext) -> SplunkKVInvestigationRepository | NullInvestigationRepository:
    if not context.splunk_token:
        return NullInvestigationRepository()
    return SplunkKVInvestigationRepository(
        SPLUNK_HOST,
        context.splunk_token,
        auth_scheme=context.splunk_auth_scheme,
    )


def _is_expired(record: dict) -> bool:
    expires = _parse_iso(record.get("expires_at"))
    return bool(expires and expires <= datetime.now(timezone.utc))
