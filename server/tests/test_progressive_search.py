"""Tests for progressive Splunk preview rendering support."""

from __future__ import annotations

from agent_mesh.investigation_models import public_artifact
from agent_mesh.job_store import InvestigationJobStore
from agent_mesh.splunk_client import SplunkClient
from agent_mesh.stream_tokens import create_stream_token, is_valid_stream_token


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def test_run_search_dispatches_preview_enabled_job_and_fetches_final_results(monkeypatch):
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
    assert post_payloads[0]["preview"] == "1"
    assert [update.status for update in updates] == ["running", "done"]
    assert result.events == [{"count": "2"}]
    assert not any(url.endswith("/services/search/v2/jobs/sid-1/results_preview") for url in get_urls)
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


def test_public_live_search_artifact_exposes_sid_without_rows():
    artifact = {
        "id": "artifact-1",
        "type": "splunk_search",
        "sid": "sid-1",
        "fields": ["user", "count"],
        "rows": [{"user": "alice", "count": "2"}],
        "messages": ["INFO: complete"],
    }

    public = public_artifact(artifact)

    assert public["sid"] == "sid-1"
    assert public["fields"] == []
    assert public["rows"] == []
    assert public["messages"] == []
    assert artifact["rows"] == [{"user": "alice", "count": "2"}]


def test_session_key_uses_splunk_authorization_scheme(monkeypatch):
    seen_headers = []

    def fake_get(_url, **kwargs):
        seen_headers.append(kwargs["headers"])
        return FakeResponse({"entry": [{"content": {"username": "alice"}}]})

    monkeypatch.setattr("agent_mesh.splunk_client.httpx.get", fake_get)

    username = SplunkClient("https://splunk.test:8089", "session-key", auth_scheme="Splunk").get_authenticated_username()

    assert username == "alice"
    assert seen_headers == [{"Authorization": "Splunk session-key"}]


def test_stream_token_is_scoped_to_investigation():
    token = create_stream_token("inv-one", 60)

    assert is_valid_stream_token("inv-one", token)
    assert not is_valid_stream_token("inv-two", token)
    assert not is_valid_stream_token("inv-one", f"{token}tampered")
