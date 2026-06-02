"""Regression tests for explicit sidecar authentication modes."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from agent_mesh import app, config
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
