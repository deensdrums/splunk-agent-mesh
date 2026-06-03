"""Tests for durable investigation KV Store snapshots."""

from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from agent_mesh import app
from agent_mesh.durable_investigations import (
    DurableInvestigationError,
    SplunkKVInvestigationRepository,
    investigation_record,
    job_from_record,
)
from agent_mesh.job_store import InvestigationJobStore
from agent_mesh.request_context import RequestContext


EVENT = {
    "type": "splunk_search",
    "title": "Search process activity",
    "text": "Checking process activity.",
    "payload": {
        "query": "index=endpoint powershell",
        "purpose": "Find suspicious PowerShell.",
        "type": "table",
    },
}


class CapturingRepository:
    def __init__(self):
        self.records: list[dict] = []

    def upsert(self, record: dict) -> None:
        self.records.append(record)

    def get(self, _investigation_id: str, username: str | None = None) -> dict | None:
        if not self.records:
            return None
        record = self.records[-1]
        if username and record["owner"]["username"] != username:
            return None
        return record


class FailingRepository:
    def upsert(self, _record: dict) -> None:
        raise DurableInvestigationError("boom")

    def get(self, _investigation_id: str, username: str | None = None) -> dict | None:
        raise DurableInvestigationError("boom")


class FakeResponse:
    def __init__(self, payload: dict | None = None, status_code: int = 200):
        self._payload = payload or {}
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _job(investigation_id: str = "inv-test") -> dict:
    return {
        "id": investigation_id,
        "owner": "alice",
        "status": "running",
        "started_at": "2026-06-03T14:22:10+00:00",
        "completed_at": None,
        "agent_order": ["spl_hunter"],
        "agents": {
            "spl_hunter": {
                "agent_id": "spl_hunter",
                "display_name": "Threat Hunter",
                "status": "iterating",
                "phase": "interpreting",
                "events": [EVENT],
                "model": "claude-haiku-4-5-20251001",
                "started_at": "2026-06-03T14:22:10+00:00",
                "completed_at": None,
                "error": None,
                "_iteration": 1,
            }
        },
        "sections": [],
        "artifacts": [{
            "id": "artifact-1",
            "agent_id": "spl_hunter",
            "type": "splunk_search",
            "status": "running",
            "_revision": 2,
            "sid": "sid-1",
            "spl": "index=endpoint powershell",
            "fields": ["host", "user"],
            "rows": [{"host": "web-01", "user": "alice"}],
            "messages": ["preview"],
        }],
        "audit": [],
        "error": None,
    }


def test_durable_record_preserves_full_events_but_excludes_rows():
    record = investigation_record(
        _job(),
        {"description": "Investigate.", "time_range": "-24h", "demo": False},
        RequestContext(username="alice", splunk_token="token", source="splunk_bridge"),
    )

    assert record["_key"] == "inv-test"
    assert record["owner"]["username"] == "alice"
    assert record["expires_at"] == "2026-07-03T14:22:10+00:00"
    assert record["events"][0]["event"] == EVENT
    assert record["events"][0]["artifact_id"] == "artifact-1"
    assert record["artifacts"][0]["revision"] == 2
    assert "rows" not in record["artifacts"][0]
    assert "messages" not in record["artifacts"][0]


def test_splunk_kv_repository_upserts_to_investigation_collection(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("agent_mesh.durable_investigations.httpx.post", fake_post)
    repository = SplunkKVInvestigationRepository(
        "https://splunk.test:8089",
        "session-key",
        app_id="splunk-agent-mesh",
        auth_scheme="Splunk",
    )

    repository.upsert({"_key": "inv-test", "investigation_id": "inv-test"})

    assert calls[0][0] == (
        "https://splunk.test:8089/servicesNS/nobody/splunk-agent-mesh/"
        "storage/collections/data/agent_mesh_investigations/inv-test"
    )
    assert calls[0][1]["headers"] == {"Authorization": "Splunk session-key"}
    assert calls[0][1]["json"]["_key"] == "inv-test"


def test_job_store_checkpoints_create_updates_and_completion():
    repository = CapturingRepository()
    store = InvestigationJobStore(durable_repository_factory=lambda _context: repository)
    context = RequestContext(username="alice", splunk_token="token")

    def runner(_payload, _context, _investigation_id, progress_callback):
        progress_callback({
            "agent_order": ["spl_hunter"],
            "agents": _job(_investigation_id)["agents"],
            "artifacts": _job(_investigation_id)["artifacts"],
        })
        return {
            **_job(_investigation_id),
            "status": "complete",
            "completed_at": "2026-06-03T14:23:00+00:00",
        }

    job = store.create({"description": "Investigate.", "demo": False}, context, runner)
    investigation_id = job["id"]

    deadline = time.time() + 5
    while time.time() < deadline and store.get(investigation_id)["status"] == "running":
        time.sleep(0.02)

    statuses = [record["status"] for record in repository.records]
    assert "running" in statuses
    assert statuses[-1] == "complete"
    assert repository.records[-1]["events"][0]["event"] == EVENT


def test_persistence_failures_are_recorded_without_breaking_job():
    store = InvestigationJobStore(durable_repository_factory=lambda _context: FailingRepository())
    context = RequestContext(username="alice", splunk_token="token")

    def runner(_payload, _context, _investigation_id, _progress_callback):
        return {
            **_job(_investigation_id),
            "status": "complete",
            "completed_at": "2026-06-03T14:23:00+00:00",
        }

    job = store.create({"description": "Investigate.", "demo": False}, context, runner)
    investigation_id = job["id"]

    deadline = time.time() + 5
    while time.time() < deadline and store.get(investigation_id)["status"] == "running":
        time.sleep(0.02)

    final = store.get(investigation_id)
    assert final["status"] == "complete"
    assert final["persistence_error"] == "boom"


def test_record_can_restore_public_job_shape_after_restart():
    record = investigation_record(_job(), {"description": "Investigate."}, RequestContext(username="alice"))

    restored = job_from_record(record)

    assert restored["id"] == "inv-test"
    assert restored["owner"] == "alice"
    assert restored["agents"]["spl_hunter"]["events"] == [EVENT]
    assert restored["artifacts"][0]["rows"] == []


def test_get_investigation_falls_back_to_durable_record(monkeypatch):
    repository = CapturingRepository()
    repository.upsert(investigation_record(_job(), {"description": "Investigate."}, RequestContext(username="alice")))
    monkeypatch.setattr(app.JOB_STORE, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app, "repository_from_context", lambda _context: repository)

    class FakeRequest:
        headers = {
            "x-splunk-user": "alice",
            "x-splunk-token": "token",
            "x-agent-mesh-source": "splunk_bridge",
        }

    result = app.get_investigation("inv-test", FakeRequest())

    assert result["id"] == "inv-test"
    assert result["agents"]["spl_hunter"]["events"] == [EVENT]


def test_durable_read_errors_surface_as_502(monkeypatch):
    monkeypatch.setattr(app, "repository_from_context", lambda _context: FailingRepository())

    with pytest.raises(HTTPException) as exc_info:
        app._durable_job("inv-test", RequestContext(username="alice", splunk_token="token"))

    assert exc_info.value.status_code == 502
