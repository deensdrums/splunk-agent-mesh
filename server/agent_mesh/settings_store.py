"""Settings and credential storage abstraction.

Production: SplunkSecureSettingsStore (Splunk Passwords REST API)
Development: DevSettingsStore (env var, refuses plaintext unless DEV_MODE=1)

Non-secret provider settings (provider name, model, base_url) are persisted to a
local JSON file in both stores — they aren't secrets and they don't require a
Splunk round-trip on every request. Only the API key requires secure storage.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

import httpx

from .security import redact_key

logger = logging.getLogger(__name__)

_LOCAL_SETTINGS_PATH = Path(__file__).parent.parent / ".agent_mesh_settings.json"


def _load_local_settings() -> dict:
    if not _LOCAL_SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(_LOCAL_SETTINGS_PATH.read_text())
    except Exception:
        return {}


def _write_local_settings(data: dict) -> None:
    _LOCAL_SETTINGS_PATH.write_text(json.dumps(data, indent=2))


def _provider_settings_from(data: dict) -> dict:
    return {
        "provider": data.get("provider", "anthropic"),
        "base_url": data.get("base_url"),
        "model": data.get("model", "claude-sonnet-4-6"),
    }


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
        try:
            return bool(self.get_api_key())
        except Exception:
            logger.exception("api_key_configured check failed.")
            return False


class DevSettingsStore(SettingsStore):
    """Local development store. Reads key from env var or local JSON file.

    Will not persist a plaintext key to disk unless AGENT_MESH_DEV_MODE=1 is set.
    The intended production path is SplunkSecureSettingsStore — set SPLUNK_TOKEN
    to activate it automatically.
    """

    def get_provider_settings(self) -> dict:
        return _provider_settings_from(_load_local_settings())

    def save_provider_settings(self, provider: str, base_url: str | None, model: str) -> None:
        data = _load_local_settings()
        data.update({"provider": provider, "base_url": base_url, "model": model})
        _write_local_settings(data)
        logger.info("Provider settings saved (dev mode).")

    def store_api_key(self, key: str) -> None:
        from .config import DEV_MODE
        if not DEV_MODE:
            msg = (
                "Plaintext API key storage is refused. To save securely, set "
                "SPLUNK_TOKEN to a Splunk admin token so the app can use the "
                "Splunk Passwords REST API. For local-disk persistence (not "
                "recommended), set AGENT_MESH_DEV_MODE=1."
            )
            logger.error(msg)
            raise PermissionError(msg)
        data = _load_local_settings()
        data["_dev_api_key"] = key
        _write_local_settings(data)
        logger.info("API key stored in dev settings (redacted: %s).", redact_key(key))

    def get_api_key(self) -> str | None:
        # Prefer env var over persisted key.
        key = os.getenv("AGENT_MESH_API_KEY")
        if key:
            return key
        return _load_local_settings().get("_dev_api_key")

    def clear_api_key(self) -> None:
        data = _load_local_settings()
        if data.pop("_dev_api_key", None) is not None:
            _write_local_settings(data)
        logger.info("API key cleared from dev settings.")


class SplunkSecureSettingsStore(SettingsStore):
    """Production store using the Splunk Passwords REST API.

    The API key is stored encrypted-at-rest in Splunk's credential storage,
    scoped to this app and the ``agent_mesh`` realm. Non-secret provider
    settings (provider name, model, base_url) are persisted to a local JSON
    file alongside the backend — they aren't secrets.

    Endpoints used:
      - POST   /servicesNS/nobody/<app>/storage/passwords            (create)
      - POST   /servicesNS/nobody/<app>/storage/passwords/<realm>:<name>:  (update)
      - GET    /servicesNS/nobody/<app>/storage/passwords/<realm>:<name>:  (read)
      - DELETE /servicesNS/nobody/<app>/storage/passwords/<realm>:<name>:  (delete)
    """

    REALM = "agent_mesh"
    NAME = "llm_api_key"

    def __init__(self, splunk_host: str, token: str, app: str, verify: bool = False, timeout: float = 10.0):
        self.splunk_host = splunk_host.rstrip("/")
        self.token = token
        self.app = app
        self.verify = verify
        self.timeout = timeout

    # ---- Provider settings (non-secret) — local file ----

    def get_provider_settings(self) -> dict:
        return _provider_settings_from(_load_local_settings())

    def save_provider_settings(self, provider: str, base_url: str | None, model: str) -> None:
        data = _load_local_settings()
        data.update({"provider": provider, "base_url": base_url, "model": model})
        _write_local_settings(data)
        logger.info("Provider settings saved.")

    # ---- API key — Splunk Passwords API ----

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _base_url(self) -> str:
        return f"{self.splunk_host}/servicesNS/nobody/{self.app}/storage/passwords"

    def _entry_url(self) -> str:
        # Splunk's key format is "<realm>:<name>:" with the trailing colon.
        key = quote(f"{self.REALM}:{self.NAME}:", safe="")
        return f"{self._base_url()}/{key}"

    def store_api_key(self, key: str) -> None:
        # Try update first; create if 404.
        update_resp = httpx.post(
            self._entry_url(),
            data={"password": key, "output_mode": "json"},
            headers=self._headers(),
            verify=self.verify,
            timeout=self.timeout,
        )
        if update_resp.status_code == 200:
            logger.info("API key updated in Splunk Passwords (redacted: %s).", redact_key(key))
            return
        if update_resp.status_code == 404:
            create_resp = httpx.post(
                self._base_url(),
                data={"name": self.NAME, "realm": self.REALM, "password": key, "output_mode": "json"},
                headers=self._headers(),
                verify=self.verify,
                timeout=self.timeout,
            )
            if create_resp.status_code in (200, 201):
                logger.info("API key created in Splunk Passwords (redacted: %s).", redact_key(key))
                return
            raise RuntimeError(
                f"Splunk passwords create failed: {create_resp.status_code} {create_resp.text[:200]}"
            )
        raise RuntimeError(
            f"Splunk passwords update failed: {update_resp.status_code} {update_resp.text[:200]}"
        )

    def get_api_key(self) -> str | None:
        resp = httpx.get(
            self._entry_url(),
            params={"output_mode": "json"},
            headers=self._headers(),
            verify=self.verify,
            timeout=self.timeout,
        )
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            logger.error("Splunk passwords read failed: %s %s", resp.status_code, resp.text[:200])
            return None
        try:
            data = resp.json()
        except ValueError:
            logger.error("Splunk passwords read returned non-JSON.")
            return None
        for entry in data.get("entry", []):
            content = entry.get("content", {})
            value = content.get("clear_password") or content.get("password")
            if value:
                return value
        return None

    def clear_api_key(self) -> None:
        resp = httpx.delete(
            self._entry_url(),
            headers=self._headers(),
            verify=self.verify,
            timeout=self.timeout,
        )
        if resp.status_code in (200, 404):
            logger.info("API key cleared from Splunk Passwords.")
            return
        raise RuntimeError(
            f"Splunk passwords delete failed: {resp.status_code} {resp.text[:200]}"
        )


def get_settings_store() -> SettingsStore:
    """Return the appropriate store for the current environment.

    If SPLUNK_TOKEN is set, the Splunk Passwords API is used. Otherwise the
    dev store is used. ``AGENT_MESH_USE_SPLUNK_STORE=0`` can force the dev
    store even when a Splunk token is present (useful for offline testing).
    """
    from .config import SPLUNK_HOST, SPLUNK_TOKEN, SPLUNK_APP_ID, USE_SPLUNK_STORE_OVERRIDE
    if SPLUNK_TOKEN and USE_SPLUNK_STORE_OVERRIDE is not False:
        return SplunkSecureSettingsStore(SPLUNK_HOST, SPLUNK_TOKEN, SPLUNK_APP_ID)
    return DevSettingsStore()
