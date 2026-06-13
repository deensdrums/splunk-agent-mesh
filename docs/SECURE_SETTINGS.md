# Splunk Agent Mesh — Secure Settings & Auth

This covers three concerns: how **LLM provider settings/keys** are stored, how
**Splunk access** is authenticated for live investigations, and the **POC
security boundaries** that are explicit design limitations.

Live mode operates on **two independent data planes**:

- **Browser-side**: the React app fetches search result rows directly from
  Splunk Web's `splunkd/__raw` proxy using the analyst's own Splunk Web cookie.
  The backend never sees or proxies these rows.
- **Backend-side**: uvicorn handles LLM calls, agent config, KV Store
  checkpoints, and investigation orchestration. Each credential mode is
  explicitly selected via environment variables, not inferred from
  `SPLUNK_TOKEN` presence.

---

## LLM provider settings

Non-secret settings (provider, base URL, model) persist to a local JSON file
beside the backend (`server/.agent_mesh_settings.json`, gitignored).

API keys go through a `SettingsStore` abstraction:

```
SettingsStore (abstract)
├── SplunkSecureSettingsStore   ← Splunk Passwords API (explicit opt-in)
└── DevSettingsStore            ← default; reads AGENT_MESH_API_KEY
```

`get_settings_store()` uses `DevSettingsStore` by default, even when a
`SPLUNK_TOKEN` is present. Set `AGENT_MESH_SETTINGS_STORE=splunk` explicitly to
activate `SplunkSecureSettingsStore`; that mode also requires `SPLUNK_TOKEN`.
The Splunk store makes real Passwords API calls.

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

`SPLUNK_TOKEN` is available to three independent, explicitly enabled features:

- `AGENT_MESH_SETTINGS_STORE=splunk` uses it for the Passwords store.
- `AGENT_MESH_CONF_SOURCE=splunk` uses it for `agents.conf` REST reads.
- `AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK=1` allows it to act as a search
  fallback when no delegated session is present.

By default, a live run with no delegated session is rejected.

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

For explicitly enabled backend features using `SPLUNK_TOKEN`:

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

---

## POC security boundaries

These are explicit design limitations for the proof-of-concept, not oversights:

- **Loopback-only deployment**: uvicorn must not be exposed beyond `127.0.0.1`.
  The `agent_mesh_bridge` trusts `X-Splunk-User` / `X-Splunk-Token` because
  they arrive from Splunk Web over loopback. External exposure would let any
  client impersonate any Splunk user.
- **Ephemeral stream-token signing secret**: `stream_tokens.py` generates the
  HMAC secret per-process via `secrets.token_bytes(32)` at import time. A
  uvicorn restart invalidates all outstanding stream tokens. Production would
  use a persisted or shared signing key.
- **In-memory job state**: running investigations live in `InvestigationJobStore`
  (in-memory). A server restart loses in-flight runs. Completed investigations
  survive in KV Store. Stream resume for interrupted sessions is not
  implemented (REL-001 postponed).
- **Single-process assumption**: the signing secret, in-memory job store, and
  durable checkpoint writer assume one uvicorn worker. Multiple workers would
  need coordination.
- **Per-user only, no RBAC**: investigation visibility is scoped to
  `owner.username`. No admin/global view, cross-user sharing, or role-based
  access control.
- **No TLS termination**: uvicorn runs plain HTTP. TLS is expected from Splunk
  Web (Tier 2) or an external reverse proxy.
- **Durable investigation ownership**: KV Store records use the analyst's
  delegated session for reads and writes. Investigation records include
  `owner.username` and the backend filters by ownership, returning 404 (not
  403) for wrong-owner access to prevent information leakage.
