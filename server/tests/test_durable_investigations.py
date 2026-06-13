"""Tests for durable investigation KV Store snapshots."""

from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from agent_mesh import app
from agent_mesh.durable_investigations import (
    DurableInvestigationError,
    SplunkKVInvestigationRepository,
    _is_expired,
    investigation_record,
    job_from_record,
    list_summary,
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
        self._store: dict[str, dict] = {}

    def upsert(self, record: dict) -> None:
        self.records.append(record)
        self._store[record["_key"]] = record

    def get(self, investigation_id: str, username: str | None = None) -> dict | None:
        record = self._store.get(investigation_id)
        if not record:
            return None
        if username and record["owner"]["username"] != username:
            return None
        return record

    def list(self, username: str, limit: int = 50) -> list[dict]:
        owned = [
            r for r in self._store.values()
            if r.get("owner", {}).get("username") == username and not _is_expired(r)
        ]
        owned.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
        return owned[:limit]


class FailingRepository:
    def upsert(self, _record: dict) -> None:
        raise DurableInvestigationError("boom")

    def get(self, _investigation_id: str, username: str | None = None) -> dict | None:
        raise DurableInvestigationError("boom")

    def list(self, _username: str, limit: int = 50) -> list[dict]:
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


# ---- STATE-003: list and load API tests ----


def _record_for(investigation_id: str, owner: str, updated_at: str, status: str = "complete") -> dict:
    job = _job(investigation_id)
    job["owner"] = owner
    job["status"] = status
    record = investigation_record(
        job,
        {"description": f"Investigate {investigation_id}."},
        RequestContext(username=owner, splunk_token="token"),
    )
    record["updated_at"] = updated_at
    return record


class _FakeListRequest:
    def __init__(self, username: str = "alice", token: str = "token"):
        self.headers = {
            "x-splunk-user": username,
            "x-splunk-token": token,
            "x-agent-mesh-source": "splunk_bridge",
        }


def test_list_summary_returns_sidebar_fields():
    record = _record_for("inv-sum", "alice", "2026-06-10T10:00:00+00:00")
    summary = list_summary(record)

    assert summary["investigation_id"] == "inv-sum"
    assert summary["owner"] == "alice"
    assert summary["status"] == "complete"
    assert summary["updated_at"] == "2026-06-10T10:00:00+00:00"
    assert "events" not in summary
    assert "artifacts" not in summary
    assert "agents" not in summary
    assert "request" not in summary


def test_list_returns_owned_records_reverse_chronological(monkeypatch):
    repository = CapturingRepository()
    repository.upsert(_record_for("inv-old", "alice", "2026-06-01T10:00:00+00:00"))
    repository.upsert(_record_for("inv-new", "alice", "2026-06-10T10:00:00+00:00"))
    monkeypatch.setattr(app, "repository_from_context", lambda _context: repository)
    monkeypatch.setattr(app.JOB_STORE, "list", lambda **_kwargs: [])

    result = app.list_investigations(_FakeListRequest(), limit=50)

    ids = [item["investigation_id"] for item in result["investigations"]]
    assert ids == ["inv-new", "inv-old"]


def test_list_excludes_other_users_records(monkeypatch):
    repository = CapturingRepository()
    repository.upsert(_record_for("inv-alice", "alice", "2026-06-10T10:00:00+00:00"))
    repository.upsert(_record_for("inv-bob", "bob", "2026-06-10T12:00:00+00:00"))
    monkeypatch.setattr(app, "repository_from_context", lambda _context: repository)
    monkeypatch.setattr(app.JOB_STORE, "list", lambda **_kwargs: [])

    result = app.list_investigations(_FakeListRequest(username="alice"), limit=50)

    ids = [item["investigation_id"] for item in result["investigations"]]
    assert ids == ["inv-alice"]
    assert "inv-bob" not in ids


def test_list_excludes_expired_records(monkeypatch):
    repository = CapturingRepository()
    record = _record_for("inv-expired", "alice", "2026-06-10T10:00:00+00:00")
    record["expires_at"] = "2020-01-01T00:00:00+00:00"
    repository.upsert(record)
    repository.upsert(_record_for("inv-valid", "alice", "2026-06-10T10:00:00+00:00"))
    monkeypatch.setattr(app, "repository_from_context", lambda _context: repository)
    monkeypatch.setattr(app.JOB_STORE, "list", lambda **_kwargs: [])

    result = app.list_investigations(_FakeListRequest(), limit=50)

    ids = [item["investigation_id"] for item in result["investigations"]]
    assert "inv-expired" not in ids
    assert "inv-valid" in ids


def test_list_respects_limit(monkeypatch):
    repository = CapturingRepository()
    for i in range(5):
        repository.upsert(_record_for(f"inv-{i:03d}", "alice", f"2026-06-{10+i}T10:00:00+00:00"))
    monkeypatch.setattr(app, "repository_from_context", lambda _context: repository)
    monkeypatch.setattr(app.JOB_STORE, "list", lambda **_kwargs: [])

    result = app.list_investigations(_FakeListRequest(), limit=2)

    assert len(result["investigations"]) == 2


def test_list_merges_memory_and_durable_deduplicates(monkeypatch):
    repository = CapturingRepository()
    repository.upsert(_record_for("inv-durable-only", "alice", "2026-06-01T10:00:00+00:00"))
    repository.upsert(_record_for("inv-both", "alice", "2026-06-05T10:00:00+00:00"))

    memory_items = [
        {
            "investigation_id": "inv-both",
            "title": "Memory version",
            "status": "running",
            "owner": "alice",
            "created_at": "2026-06-05T10:00:00+00:00",
            "updated_at": "2026-06-10T10:00:00+00:00",
            "completed_at": None,
            "event_count": 3,
            "artifact_count": 1,
        },
    ]
    monkeypatch.setattr(app, "repository_from_context", lambda _context: repository)
    monkeypatch.setattr(app.JOB_STORE, "list", lambda **_kwargs: memory_items)

    result = app.list_investigations(_FakeListRequest(), limit=50)

    ids = [item["investigation_id"] for item in result["investigations"]]
    assert ids.count("inv-both") == 1
    both_item = next(item for item in result["investigations"] if item["investigation_id"] == "inv-both")
    assert both_item["status"] == "running"
    assert "inv-durable-only" in ids


def test_list_graceful_when_durable_fails(monkeypatch):
    monkeypatch.setattr(app, "repository_from_context", lambda _context: FailingRepository())
    memory_items = [
        {
            "investigation_id": "inv-mem",
            "title": "In memory",
            "status": "running",
            "owner": "alice",
            "created_at": "2026-06-10T10:00:00+00:00",
            "updated_at": "2026-06-10T10:00:00+00:00",
            "completed_at": None,
            "event_count": 0,
            "artifact_count": 0,
        },
    ]
    monkeypatch.setattr(app.JOB_STORE, "list", lambda **_kwargs: memory_items)

    result = app.list_investigations(_FakeListRequest(), limit=50)

    assert len(result["investigations"]) == 1
    assert result["investigations"][0]["investigation_id"] == "inv-mem"


def test_list_empty_in_dev_mode(monkeypatch):
    monkeypatch.setattr(app.JOB_STORE, "list", lambda **_kwargs: [])

    result = app.list_investigations(
        _FakeListRequest(username="dev-user", token=""),
        limit=50,
    )

    assert result["investigations"] == []


def test_get_investigation_returns_400_for_malformed_id():
    with pytest.raises(HTTPException) as exc_info:
        app.get_investigation("../../../etc/passwd", _FakeListRequest())
    assert exc_info.value.status_code == 400


def test_get_investigation_returns_400_for_empty_id():
    with pytest.raises(HTTPException) as exc_info:
        app.get_investigation("", _FakeListRequest())
    assert exc_info.value.status_code == 400


def test_get_investigation_returns_404_for_wrong_owner(monkeypatch):
    repository = CapturingRepository()
    repository.upsert(_record_for("inv-alice", "alice", "2026-06-10T10:00:00+00:00"))
    monkeypatch.setattr(app.JOB_STORE, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app, "repository_from_context", lambda _context: repository)

    with pytest.raises(HTTPException) as exc_info:
        app.get_investigation("inv-alice", _FakeListRequest(username="bob"))

    assert exc_info.value.status_code == 404


def test_get_investigation_status_returns_400_for_malformed_id():
    with pytest.raises(HTTPException) as exc_info:
        app.get_investigation_status("../../bad", _FakeListRequest())
    assert exc_info.value.status_code == 400


def test_job_store_list_returns_owned_jobs():
    store = InvestigationJobStore()
    context_alice = RequestContext(username="alice", splunk_token="token")
    context_bob = RequestContext(username="bob", splunk_token="token")

    def noop_runner(_payload, _context, _id, _cb):
        return {"id": _id, "status": "complete", "completed_at": "2026-06-10T10:00:00+00:00",
                "agents": {}, "agent_order": [], "sections": [], "artifacts": []}

    store.create({"description": "Alice investigation", "demo": False}, context_alice, noop_runner)
    store.create({"description": "Bob investigation", "demo": False}, context_bob, noop_runner)

    alice_list = store.list(username="alice")
    assert len(alice_list) == 1
    assert alice_list[0]["owner"] == "alice"
    assert alice_list[0]["title"] == "Alice investigation"
