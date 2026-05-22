# Splunk Agent Mesh — Secure Settings

## How LLM Provider Settings Are Stored

Non-secret settings (provider name, base URL, model name) are persisted to a
local JSON file alongside the backend (`server/.agent_mesh_settings.json`,
gitignored). They aren't secrets so they don't need a Splunk round-trip.

## How API Keys Are Stored

API keys go through a `SettingsStore` abstraction:

```
SettingsStore (abstract)
├── SplunkSecureSettingsStore   ← used when SPLUNK_TOKEN is set
└── DevSettingsStore            ← fallback when SPLUNK_TOKEN is absent
```

The factory `get_settings_store()` activates `SplunkSecureSettingsStore`
whenever `SPLUNK_TOKEN` is set. To force the dev store even with a token
present (offline testing), set `AGENT_MESH_USE_SPLUNK_STORE=0`.

### SplunkSecureSettingsStore

Uses Splunk's REST Passwords API to store and retrieve the LLM key:

| Operation | Endpoint |
|---|---|
| Create | `POST /servicesNS/nobody/splunk-agent-mesh/storage/passwords` (form: `name=llm_api_key&realm=agent_mesh&password=...`) |
| Update | `POST /servicesNS/nobody/splunk-agent-mesh/storage/passwords/agent_mesh:llm_api_key:` (form: `password=...`) |
| Read   | `GET  /servicesNS/nobody/splunk-agent-mesh/storage/passwords/agent_mesh:llm_api_key:?output_mode=json` |
| Delete | `DELETE /servicesNS/nobody/splunk-agent-mesh/storage/passwords/agent_mesh:llm_api_key:` |

Authentication: `Authorization: Bearer <SPLUNK_TOKEN>`. The token is a Splunk
admin token (create via Splunk Web: **Settings → Tokens**) with the
capabilities listed below.

`store_api_key()` tries update first and falls back to create on 404, so the
same call handles both new entries and overwrites.

### DevSettingsStore

Reads from the `AGENT_MESH_API_KEY` environment variable. Refuses to store a
plaintext key to disk unless `AGENT_MESH_DEV_MODE=1` is explicitly set.

## Required Splunk Capabilities

For the backend's `SPLUNK_TOKEN`:

- `list_storage_passwords` — read stored credentials
- `edit_storage_passwords` — write/delete credentials
- `rest_properties_get` / `rest_properties_set` — read/write conf via REST (for `agents.conf` access)

The simplest path is to issue the token to an `admin` role user.

## How the Settings Page Works

1. User opens **Settings** in Splunk Agent Mesh.
2. UI calls `GET /api/v1/settings` — response includes `storage_backend`
   so the UI can tell the user whether Splunk Passwords or Dev mode is active.
3. User picks provider, model, base URL (if custom), and pastes API key.
4. User clicks **Save**.
5. UI calls `POST /api/v1/settings` with all fields.
6. Backend validates inputs (Pydantic validators on provider/model/base_url).
7. Backend persists provider settings to the local JSON file.
8. Backend stores the API key via the active `SettingsStore`.
9. Backend returns `{ "saved": true, "api_key_configured": true }`.
10. UI shows the success message; the API key field clears.

## What Must Never Be Logged

- API keys (full or partial, except redacted form via `security.redact_key`)
- Splunk session keys or admin tokens
- Any `Authorization` header values

## Redaction Requirements

`security.redact_key(key)` returns the first 4 chars plus `****`. Used only in
log messages when confirming a key was received. Never in HTTP responses;
responses return `api_key_configured: bool` only.

## Test Connection Behavior

`POST /api/v1/settings/test`:

1. Retrieves the stored API key from the active `SettingsStore`.
2. Calls `LLMProvider.test_connection()` (sends a minimal LLM request).
3. Returns `{ "success": true, "latency_ms": 123, "model": "..." }` or
   `{ "success": false, "error": "..." }`.
4. The API key is never included in the response.

## Clear Credentials

`DELETE /api/v1/settings/credentials`:

- Calls `SettingsStore.clear_api_key()`.
- Does not clear provider/model settings — the user may want to re-enter a key
  without re-selecting the provider.
- Returns `{ "cleared": true }`.
