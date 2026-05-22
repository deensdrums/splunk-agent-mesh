# Splunk Agent Mesh — Secure Settings

## How LLM Provider Settings Are Stored

Non-secret settings (provider name, base URL, model name) are stored in:
- **MVP (local dev)**: In-process dictionary, persisted to a local `settings.json` under `server/` (gitignored)
- **Production Splunk**: `$SPLUNK_HOME/etc/apps/splunk-agent-mesh/local/agent_mesh.conf` via Splunk's conf API

## How API Keys Are Stored

API keys go through a `SettingsStore` abstraction:

```
SettingsStore (abstract)
├── SplunkSecureSettingsStore   ← production: Splunk Passwords API (encrypted at rest)
└── DevSettingsStore            ← local dev only: env var or refuses plaintext
```

### SplunkSecureSettingsStore
Uses `POST /services/storage/passwords` to store the API key encrypted by Splunk's credential storage. The key is retrieved via `GET /services/storage/passwords/<realm>:<name>:` at request time. The raw key is never written to disk in plaintext.

### DevSettingsStore
Reads from the `AGENT_MESH_API_KEY` environment variable. Refuses to store a plaintext key unless `AGENT_MESH_DEV_MODE=1` is also set. If `DEV_MODE` is not set and no env var key is found, the store returns `api_key_configured: false`.

## Which Splunk Capabilities May Be Required

For production deployment:
- `admin_all_objects` or `list_storage_passwords` — read stored credentials
- `edit_storage_passwords` — write credentials
- `search` — run SPL searches on behalf of the user
- `rest_apps_management` — if registering custom REST endpoint

## How the Settings Page Works

1. User opens Settings tab in Splunk Agent Mesh.
2. User selects provider (Anthropic / OpenRouter / Custom).
3. User enters base URL (if Custom), model name, and API key.
4. User clicks **Save**.
5. Frontend calls `POST /api/v1/settings` with all fields.
6. Backend:
   a. Validates provider, base URL, model name format.
   b. Stores provider/base URL/model in conf (non-secret).
   c. Passes API key to `SettingsStore.store_api_key()`.
   d. Returns `{ "saved": true, "api_key_configured": true }`.
7. Frontend shows "API key configured" badge. Key is NOT displayed again.

## What Must Never Be Logged

- API keys (full or partial, except redacted form)
- Session tokens
- Splunk credentials
- Any `Authorization` header values

## Redaction Requirements

The `security.py` module provides `redact_key(key)` → returns first 4 chars + `****`. This is used:
- In log messages when confirming key is present
- Never in HTTP responses (responses return `api_key_configured: bool` only)

## Test Connection Behavior

`POST /api/v1/settings/test`:
1. Retrieves stored API key from `SettingsStore`.
2. Calls `LLMProvider.test_connection()` — sends a minimal API request (e.g., list models or a 1-token completion).
3. Returns `{ "success": true, "latency_ms": 123, "model": "claude-3-5-sonnet-20241022" }` or `{ "success": false, "error": "..." }`.
4. API key is NOT included in the response under any circumstances.

## Clear Credentials

`DELETE /api/v1/settings/credentials`:
- Calls `SettingsStore.clear_api_key()`.
- Does not clear provider/model settings (user may want to re-enter key without reconfiguring provider).
- Returns `{ "cleared": true }`.
