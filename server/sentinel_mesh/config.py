"""Runtime configuration loaded from environment."""

import os
from dotenv import load_dotenv

load_dotenv()

# Set SENTINEL_MESH_DEV_MODE=1 to allow DevSettingsStore to accept keys.
DEV_MODE: bool = os.getenv("SENTINEL_MESH_DEV_MODE", "0") == "1"

# Set SENTINEL_MESH_USE_SPLUNK_STORE=1 to opt in to the (unimplemented) Splunk
# Passwords-API-backed store. Until that store is wired up, leave this off.
USE_SPLUNK_STORE: bool = os.getenv("SENTINEL_MESH_USE_SPLUNK_STORE", "0") == "1"

# CORS origin(s) for the frontend. Comma-separated list.
CORS_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("SENTINEL_MESH_CORS_ORIGINS", "http://localhost:8080,http://localhost:3000").split(",")
    if o.strip()
]

# Splunk REST API base URL (used by splunk_client.py)
SPLUNK_HOST: str = os.getenv("SPLUNK_HOST", "https://localhost:8089")
SPLUNK_TOKEN: str = os.getenv("SPLUNK_TOKEN", "")

# Log level
LOG_LEVEL: str = os.getenv("SENTINEL_MESH_LOG_LEVEL", "INFO")
