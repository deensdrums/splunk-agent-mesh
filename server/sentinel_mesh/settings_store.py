"""Settings and credential storage abstraction.

Production: SplunkSecureSettingsStore (Splunk Passwords API)
Development: DevSettingsStore (env var, refuses plaintext unless DEV_MODE=1)
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from .security import redact_key

logger = logging.getLogger(__name__)

_LOCAL_SETTINGS_PATH = Path(__file__).parent.parent / ".sentinel_mesh_settings.json"


class SettingsStore(ABC):
    @abstractmethod
    def get_provider_settings(self) -> dict:
        """Return provider, base_url, model. Never return api_key."""

    @abstractmethod
    def save_provider_settings(self, provider: str, base_url: str | None, model: str) -> None:
        """Persist non-secret provider settings."""

    @abstractmethod
    def store_api_key(self, key: str) -> None:
        """Encrypt and persist the API key."""

    @abstractmethod
    def get_api_key(self) -> str | None:
        """Retrieve the API key for in-process use only. Never expose in responses."""

    @abstractmethod
    def clear_api_key(self) -> None:
        """Remove the stored API key."""

    def api_key_configured(self) -> bool:
        key = self.get_api_key()
        return bool(key)


class DevSettingsStore(SettingsStore):
    """Local development store. Reads key from env var.

    Will not persist a plaintext key to disk unless SENTINEL_MESH_DEV_MODE=1 is set.
    """

    def get_provider_settings(self) -> dict:
        if _LOCAL_SETTINGS_PATH.exists():
            try:
                data = json.loads(_LOCAL_SETTINGS_PATH.read_text())
                return {
                    "provider": data.get("provider", "anthropic"),
                    "base_url": data.get("base_url"),
                    "model": data.get("model", "claude-sonnet-4-6"),
                }
            except Exception:
                pass
        return {"provider": "anthropic", "base_url": None, "model": "claude-sonnet-4-6"}

    def save_provider_settings(self, provider: str, base_url: str | None, model: str) -> None:
        existing: dict = {}
        if _LOCAL_SETTINGS_PATH.exists():
            try:
                existing = json.loads(_LOCAL_SETTINGS_PATH.read_text())
            except Exception:
                pass
        existing.update({"provider": provider, "base_url": base_url, "model": model})
        _LOCAL_SETTINGS_PATH.write_text(json.dumps(existing, indent=2))
        logger.info("Provider settings saved (dev mode).")

    def store_api_key(self, key: str) -> None:
        from .config import DEV_MODE
        if not DEV_MODE:
            logger.error(
                "Refused to store API key in plaintext. Set SENTINEL_MESH_DEV_MODE=1 to enable "
                "local key persistence, or set SENTINEL_MESH_API_KEY env var."
            )
            raise PermissionError(
                "Plaintext key storage refused. Set SENTINEL_MESH_DEV_MODE=1 or use SENTINEL_MESH_API_KEY env var."
            )
        existing: dict = {}
        if _LOCAL_SETTINGS_PATH.exists():
            try:
                existing = json.loads(_LOCAL_SETTINGS_PATH.read_text())
            except Exception:
                pass
        existing["_dev_api_key"] = key
        _LOCAL_SETTINGS_PATH.write_text(json.dumps(existing, indent=2))
        logger.info("API key stored in dev settings (redacted: %s).", redact_key(key))

    def get_api_key(self) -> str | None:
        # Prefer env var over persisted key.
        key = os.getenv("SENTINEL_MESH_API_KEY")
        if key:
            return key
        if _LOCAL_SETTINGS_PATH.exists():
            try:
                data = json.loads(_LOCAL_SETTINGS_PATH.read_text())
                return data.get("_dev_api_key")
            except Exception:
                pass
        return None

    def clear_api_key(self) -> None:
        if _LOCAL_SETTINGS_PATH.exists():
            try:
                data = json.loads(_LOCAL_SETTINGS_PATH.read_text())
                data.pop("_dev_api_key", None)
                _LOCAL_SETTINGS_PATH.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
        logger.info("API key cleared from dev settings.")


class SplunkSecureSettingsStore(SettingsStore):
    """Production store using Splunk Passwords API.

    Requires a valid Splunk session token and host configured via environment or Splunk context.

    This is a stub implementation. Integrate with:
      POST /services/storage/passwords  to store
      GET  /services/storage/passwords/<realm>:<name>:  to retrieve
    """

    REALM = "sentinel_mesh"
    NAME = "llm_api_key"

    def __init__(self, splunk_host: str, token: str):
        self.splunk_host = splunk_host
        self.token = token

    def _headers(self) -> dict:
        return {"Authorization": f"Splunk {self.token}", "Content-Type": "application/x-www-form-urlencoded"}

    def get_provider_settings(self) -> dict:
        # TODO: read from /services/properties/sentinel_mesh/settings
        raise NotImplementedError("SplunkSecureSettingsStore.get_provider_settings not yet wired.")

    def save_provider_settings(self, provider: str, base_url: str | None, model: str) -> None:
        # TODO: POST to /services/configs/conf-sentinel_mesh
        raise NotImplementedError("SplunkSecureSettingsStore.save_provider_settings not yet wired.")

    def store_api_key(self, key: str) -> None:
        # TODO: POST /services/storage/passwords
        raise NotImplementedError("SplunkSecureSettingsStore.store_api_key not yet wired.")

    def get_api_key(self) -> str | None:
        # TODO: GET /services/storage/passwords/sentinel_mesh:llm_api_key:
        raise NotImplementedError("SplunkSecureSettingsStore.get_api_key not yet wired.")

    def clear_api_key(self) -> None:
        # TODO: DELETE /services/storage/passwords/sentinel_mesh:llm_api_key:
        raise NotImplementedError("SplunkSecureSettingsStore.clear_api_key not yet wired.")


def get_settings_store() -> SettingsStore:
    """Return the appropriate store for the current environment."""
    from .config import SPLUNK_HOST, SPLUNK_TOKEN
    if SPLUNK_TOKEN:
        return SplunkSecureSettingsStore(SPLUNK_HOST, SPLUNK_TOKEN)
    return DevSettingsStore()
