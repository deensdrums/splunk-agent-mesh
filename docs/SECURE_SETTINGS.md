# Splunk Agent Mesh — Secure Settings & Auth

This covers two concerns: how **LLM provider settings/keys** are stored, and how
**Splunk access** is authenticated for live investigations.

---

## LLM provider settings

Non-secret settings (provider, base URL, model) persist to a local JSON file
beside the backend (`server/.agent_mesh_settings.json`, gitignored).

API keys go through a `SettingsStore` abstraction:

```
SettingsStore (abstract)
├── SplunkSecureSettingsStore   ← Splunk Passwords API (used when SPLUNK_TOKEN is set)
└── DevSettingsStore            ← fallback when SPLUNK_TOKEN is absent
```

`get_settings_store()` activates `SplunkSecureSettingsStore` whenever
`SPLUNK_TOKEN` is set. Force the dev store with `AGENT_MESH_USE_SPLUNK_STORE=0`.
(`SplunkSecureSettingsStore` is currently stubbed; `DevSettingsStore` is used in
the active deployment.)

### SplunkSecureSettingsStore (design)

Stores the LLM key via the Passwords API
(`/servicesNS/nobody/splunk-agent-mesh/storage/passwords`, realm
`agent_mesh`, name `llm_api_key`); `store_api_key()` tries update then falls
back to create. Auth: `Authorization: Bearer <SPLUNK_TOKEN>`.

### DevSettingsStore

Reads `AGENT_MESH_API_KEY`. Refuses to write a plaintext key to disk unless
`AGENT_MESH_DEV_MODE=1`.

---

## Splunk authentication for investigations

Live investigations use the **analyst's own Splunk session**, not a shared admin
token.

1. In Splunk Web, the React app calls the `agent_mesh_bridge` custom REST
   endpoint. Splunk authenticates the request, and the bridge forwards it to
   uvicorn with `X-Splunk-User` (username) and `X-Splunk-Token` (session key).
2. `request_context.context_from_request` reads those headers and sets the auth
   scheme to `Splunk` (vs. `Bearer` for a service token).
3. Before a live run, the backend validates the session via
   `/services/authentication/current-context` and confirms the returned username
   matches the requesting user — otherwise the request is rejected (401/403).
4. `SplunkClient` runs all searches with that session key.

### Service-token fallback

`SPLUNK_TOKEN` is used for conf reads and the Passwords store, and can act as a
**search fallback** only when explicitly enabled with
`AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK=1` and no delegated session is
present. By default, a live run with no delegated session is rejected.

### SSE stream tokens

`EventSource` cannot send auth headers, so `/investigations/start` returns a
short-lived HMAC-signed `stream_token` (`stream_tokens.py`, default TTL 4h, set
via `AGENT_MESH_STREAM_TOKEN_TTL_SECONDS`). `/stream` rejects missing/invalid
tokens. The signing secret is per-process — see the note in `docs/ARCHITECTURE.md`.

### Result-row minimization

The JSON API returns search artifacts **without rows** (`public_artifact` /
`public_investigation`); the browser fetches preview and final rows itself from
Splunk Web's authenticated `splunkd/__raw` proxy. Demo artifacts keep their rows.

### Trust boundary

The bridge trusts `X-Splunk-User` / `X-Splunk-Token` because they originate from
Splunk Web over loopback. **uvicorn must not be exposed beyond loopback** — any
client that can set those headers would be trusted.

---

## Required Splunk capabilities

For the backend's `SPLUNK_TOKEN` (conf + Passwords store):

- `list_storage_passwords`, `edit_storage_passwords` — credential storage
- `rest_properties_get` / `rest_properties_set` — read conf via REST

Delegated analyst sessions carry whatever search capabilities that user already
has — searches run with least privilege, as that analyst.

---

## Settings page flow

1. **Settings** → `GET /api/v1/settings` (includes `storage_backend`).
2. User picks provider/model/base URL and pastes an API key → **Save**.
3. `POST /api/v1/settings` validates (Pydantic), persists non-secret settings to
   JSON, stores the key via the active `SettingsStore`, returns
   `{ saved: true, api_key_configured: true }`.
4. `POST /api/v1/settings/test` retrieves the key and calls
   `LLMProvider.test_connection()`.
5. `DELETE /api/v1/settings/credentials` clears the key (keeps provider settings).

## What must never be logged

- API keys (except the redacted form from `security.redact_key`, first 4 chars +
  `****`).
- Splunk session keys or admin tokens; any `Authorization` header values.

`AGENT_MESH_LOG_LLM=1` logs full LLM requests/responses for debugging — keep it
off outside local debugging since prompts/results may contain sensitive data.
