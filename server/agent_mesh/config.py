"""Runtime configuration loaded from environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Set AGENT_MESH_DEV_MODE=1 to allow DevSettingsStore to accept keys.
DEV_MODE: bool = os.getenv("AGENT_MESH_DEV_MODE", "0") == "1"

# By default the Splunk Passwords store activates whenever SPLUNK_TOKEN is set.
# AGENT_MESH_USE_SPLUNK_STORE can override that explicitly:
#   "1" / "true" / "yes" -> force Splunk store (still requires SPLUNK_TOKEN)
#   "0" / "false" / "no" -> force dev store even when SPLUNK_TOKEN is set
#   unset                -> auto (Splunk if token, dev otherwise)
def _parse_override(value: str | None) -> bool | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return None


USE_SPLUNK_STORE_OVERRIDE: bool | None = _parse_override(os.getenv("AGENT_MESH_USE_SPLUNK_STORE"))

# CORS origin(s) for the frontend. Comma-separated list.
CORS_ORIGINS: list[str] = [
    o.strip() for o in os.getenv(
        "AGENT_MESH_CORS_ORIGINS",
        "http://localhost:8000,http://localhost:8080,http://localhost:3000",
    ).split(",")
    if o.strip()
]

# Splunk REST API base URL.
SPLUNK_HOST: str = os.getenv("SPLUNK_HOST", "https://localhost:8089")
SPLUNK_TOKEN: str = os.getenv("SPLUNK_TOKEN", "")

# Splunk app id — used to scope REST calls (configs, passwords, search).
SPLUNK_APP_ID: str = os.getenv("AGENT_MESH_SPLUNK_APP_ID", "splunk-agent-mesh")

# Paths to agents.conf for the FileConfReader fallback. Later paths override earlier.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_APP_DEFAULT_CONF = _REPO_ROOT / "packages" / "agent-mesh" / "src" / "main" / "resources" / "splunk" / "default" / "agents.conf"
_APP_LOCAL_CONF = _REPO_ROOT / "packages" / "agent-mesh" / "src" / "main" / "resources" / "splunk" / "local" / "agents.conf"
AGENTS_CONF_PATHS: list[Path] = [_APP_DEFAULT_CONF, _APP_LOCAL_CONF]

# Log level
LOG_LEVEL: str = os.getenv("AGENT_MESH_LOG_LEVEL", "INFO")
