"""Regression tests for explicit sidecar authentication modes."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from agent_mesh import app, config
from agent_mesh.agents.agent_config import AgentConfig
from agent_mesh.conf_reader import FileConfReader, SplunkRestConfReader, get_conf_reader
from agent_mesh.settings_store import (
    DevSettingsStore,
    SplunkSecureSettingsStore,
    SplunkSettingsStoreError,
    get_settings_store,
)


class FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class FakeConfReader:
    def get_agents(self):
        return [
            AgentConfig(
                id="spl_hunter",
                display_name="Threat Hunter",
                description="Investigates incidents.",
                system_prompt="Investigate.",
                model="claude-haiku-4-5-20251001",
                agent_role="primary",
            )
        ]


class CapturingStore(DevSettingsStore):
    def __init__(self):
        self.saved = None

    def get_provider_settings(self) -> dict:
        return {
            "provider": "anthropic",
            "base_url": None,
            "model": "legacy-provider-model",
        }

    def save_provider_settings(self, provider: str, base_url: str | None, model: str) -> None:
        self.saved = {"provider": provider, "base_url": base_url, "model": model}

    def get_api_key(self) -> str | None:
        return None


def test_service_token_does_not_silently_select_splunk_settings_store(monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_STORE_BACKEND", "dev")
    monkeypatch.setattr(config, "SPLUNK_TOKEN", "service-token")

    assert isinstance(get_settings_store(), DevSettingsStore)


def test_splunk_settings_store_requires_explicit_mode_and_token(monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_STORE_BACKEND", "splunk")
    monkeypatch.setattr(config, "SPLUNK_TOKEN", "")

    with pytest.raises(RuntimeError, match="requires SPLUNK_TOKEN"):
        get_settings_store()

    monkeypatch.setattr(config, "SPLUNK_TOKEN", "service-token")
    assert isinstance(get_settings_store(), SplunkSecureSettingsStore)


def test_service_token_does_not_silently_select_rest_conf_reader(monkeypatch):
    monkeypatch.setattr(config, "CONF_SOURCE", "file")
    monkeypatch.setattr(config, "SPLUNK_TOKEN", "service-token")

    assert isinstance(get_conf_reader(), FileConfReader)


def test_rest_conf_reader_requires_explicit_mode_and_token(monkeypatch):
    monkeypatch.setattr(config, "CONF_SOURCE", "splunk")
    monkeypatch.setattr(config, "SPLUNK_TOKEN", "")

    with pytest.raises(RuntimeError, match="requires SPLUNK_TOKEN"):
        get_conf_reader()

    monkeypatch.setattr(config, "SPLUNK_TOKEN", "service-token")
    assert isinstance(get_conf_reader(), SplunkRestConfReader)


def test_file_conf_reader_parses_subagent_lifecycle_fields(tmp_path):
    conf_path = tmp_path / "agents.conf"
    conf_path.write_text(
        """
[default]
model = fake-model

[agent:search_optimizer]
display_name = Search Optimizer
system_prompt = Optimize SPL.
agent_role = subagent
subagent_kind = search_optimizer
invoke_policy = before_search
output_contract = json
required = 1
failure_policy = fail_run
""".strip()
    )

    agents = FileConfReader([conf_path]).get_agents()

    assert len(agents) == 1
    agent = agents[0]
    assert agent.id == "search_optimizer"
    assert agent.agent_role == "subagent"
    assert agent.subagent_kind == "search_optimizer"
    assert agent.invoke_policy == "before_search"
    assert agent.output_contract == "json"
    assert agent.required is True
    assert agent.failure_policy == "fail_run"


def test_splunk_settings_store_preserves_upstream_auth_status(monkeypatch):
    monkeypatch.setattr(
        "agent_mesh.settings_store.httpx.post",
        lambda *_args, **_kwargs: FakeResponse(401, "not properly authenticated"),
    )
    store = SplunkSecureSettingsStore("https://splunk.test:8089", "expired", "splunk-agent-mesh")

    with pytest.raises(SplunkSettingsStoreError) as exc_info:
        store.store_api_key("secret")

    assert exc_info.value.status_code == 401


def test_settings_api_preserves_splunk_store_auth_status(monkeypatch):
    class FailingStore(DevSettingsStore):
        def store_api_key(self, _key: str) -> None:
            raise SplunkSettingsStoreError("update", 403, "forbidden")

    monkeypatch.setattr(app, "get_settings_store", lambda: FailingStore())

    with pytest.raises(HTTPException) as exc_info:
        app.save_settings(
            app.SaveSettingsRequest(
                provider="anthropic",
                model="claude-sonnet-4-6",
                api_key="secret",
            )
        )

    assert exc_info.value.status_code == 403


def test_settings_api_reports_effective_harness_model_from_agents_conf(monkeypatch):
    monkeypatch.setattr(app, "get_settings_store", lambda: CapturingStore())
    monkeypatch.setattr(app, "get_conf_reader", lambda: FakeConfReader())
    monkeypatch.setattr(app, "CONF_SOURCE", "file")

    settings = app.get_settings()

    assert settings["model"] == "legacy-provider-model"
    assert settings["effective_model"] == {
        "model": "claude-haiku-4-5-20251001",
        "agent_id": "spl_hunter",
        "agent_name": "Threat Hunter",
        "conf_source": "file",
        "editable": False,
        "policy": "read_only_agents_conf",
        "error": None,
    }


def test_settings_save_preserves_legacy_provider_model_when_request_omits_model(monkeypatch):
    store = CapturingStore()
    monkeypatch.setattr(app, "get_settings_store", lambda: store)

    response = app.save_settings(app.SaveSettingsRequest(provider="anthropic"))

    assert response == {"saved": True, "api_key_configured": False}
    assert store.saved == {
        "provider": "anthropic",
        "base_url": None,
        "model": "legacy-provider-model",
    }
