"""Tests for progressive Splunk preview rendering support."""

from __future__ import annotations

from agent_mesh.job_store import InvestigationJobStore
from agent_mesh.splunk_client import SplunkClient


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def test_run_search_dispatches_preview_enabled_job_and_streams_preview(monkeypatch):
    post_payloads = []
    get_urls = []
    statuses = iter([
        {"entry": [{"content": {"dispatchState": "RUNNING"}}]},
        {"entry": [{"content": {"dispatchState": "DONE"}}]},
    ])

    def fake_post(url, **kwargs):
        post_payloads.append(kwargs["data"])
        return FakeResponse({"sid": "sid-1"})

    def fake_get(url, **_kwargs):
        get_urls.append(url)
        if url.endswith("/services/search/jobs/sid-1"):
            return FakeResponse(next(statuses))
        if url.endswith("/services/search/v2/jobs/sid-1/results_preview"):
            return FakeResponse({"results": [{"count": "1"}], "fields": [{"name": "count"}]})
        if url.endswith("/services/search/v2/jobs/sid-1/results"):
            return FakeResponse({"results": [{"count": "2"}], "fields": [{"name": "count"}]})
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("agent_mesh.splunk_client.httpx.post", fake_post)
    monkeypatch.setattr("agent_mesh.splunk_client.httpx.get", fake_get)
    monkeypatch.setattr("agent_mesh.splunk_client.sleep", lambda _seconds: None)
    updates = []

    result = SplunkClient("https://splunk.test:8089", "token").run_search(
        "index=main | stats count", on_update=updates.append,
    )

    assert post_payloads[0]["status_buckets"] == "300"
    assert [update.status for update in updates] == ["running", "running", "done"]
    assert updates[1].events == [{"count": "1"}]
    assert result.events == [{"count": "2"}]
    assert any(url.endswith("/services/search/v2/jobs/sid-1/results_preview") for url in get_urls)
    assert any(url.endswith("/services/search/v2/jobs/sid-1/results") for url in get_urls)


def test_job_store_replaces_artifact_revisions_in_place():
    store = InvestigationJobStore()
    store._jobs["inv-test"] = {"status": "running", "artifacts": []}

    store.apply_update("inv-test", {"artifacts": [{"id": "artifact-1", "_revision": 1, "status": "running"}]})
    store.apply_update("inv-test", {"artifacts": [{"id": "artifact-1", "_revision": 2, "status": "done"}]})

    artifacts = store.get("inv-test")["artifacts"]
    assert len(artifacts) == 1
    assert artifacts[0]["_revision"] == 2
    assert artifacts[0]["status"] == "done"
