# Splunk Agent Mesh

MIT License.  See ./LICENSE in the root directory of this repository.

**An agentic SOC investigation copilot for Splunk Enterprise.**

The analyst describes an alert; a **Threat Hunter** agent investigates it live —
narrating its reasoning, running real SPL searches against Splunk, summarizing
what it finds, and delegating a written report to an internal reporting agent.
Everything streams into a single console-style transcript as it happens.

The Threat Hunter speaks one language: a strict **structured event stream**
(`narration`, `splunk_search`, `result_summary`, `finding`, `handoff`,
`final`). The harness validates every response, runs at most one action per
turn, and feeds results back so the agent can react to evidence.

---

## How it works

```
agents.conf  (Splunk app default + local)
     │
     ▼
ConfReader ──▶ Orchestrator ──▶ Threat Hunter (agentic event loop)
                                    │   ▲          │
                  one action/turn   │   │ results  │ handoff
                                    ▼   │          ▼
                              splunk_search    Reporting sub-agent
                              (live Splunk)    (internal, summarized back)
                                    │
                                    ▼
                       structured events + artifacts
                                    │
                       SSE ─────────▼──────────▶ Browser transcript
                                                 (progressive, live charts)
```

- **Backend**: FastAPI on port 8765. Reads `agents.conf` from file (default)
  or via Splunk REST (opt-in).
- **One visible agent**: the Threat Hunter (`spl_hunter`). The reporting agent
  (`executive_brief`) is an internal sub-agent invoked only via `handoff`; its
  output is summarized back into the Threat Hunter's event stream. The UI never
  shows it as a peer.
- **Structured contract**: the Threat Hunter returns a single JSON object
  `{"events": [...]}`. The harness validates it (`agents/events.py`); invalid
  output is rejected with a corrective retry, never shown to the user.
- **Harness-driven loop**: the agent proposes; the harness executes. At most one
  external action per turn (a `splunk_search` or a `handoff`), taken from the
  last event. Provider-agnostic — it uses plain `complete()`, not vendor
  tool-use APIs.
- **Live search**: `splunk_search` events run against Splunk with the analyst's
  **delegated session**. Preview rows stream into the cards as the search runs.
- **Progressive UI**: events stream over SSE and paint one at a time into a
  scrollable transcript with inline charts and a persistent status bar.

---

## Hackathon Track

Splunk Agentic Ops Hackathon

---

## Repo Structure

```
packages/
  agent-mesh-ui/                  # @splunk/agent-mesh-ui — React component library
    src/
      pages/                      # InvestigationPage, SettingsPage, AboutPage
      components/
        InvestigationReport.tsx   # Console transcript: toolbar, scroll area, status bar
        HistorySidebar.tsx        # Collapsible investigation history rail + panel
        EventRenderer.tsx         # Renders one structured event (colored accent blocks)
        ArtifactRenderer.tsx      # Search results → Column/Line/Pie/Bar/Table/Single
        MarkdownView.tsx          # Sanitized markdown (final-summary / legacy fallback)
        AgentStatusBadge.tsx
        legacy/                   # Archived structured-output components (unused)
      hooks/
        useStaggeredReveal.ts     # Reveal events one at a time
        useInvestigationUrl.ts    # URL-addressable sessions via ?id= query parameter
      services/
        apiClient.ts              # HTTP + SSE client (routes via Splunk bridge in Web)
        splunkWeb.ts              # Splunk Web runtime detection + REST URL helper
        splunkSearchResults.ts    # Browser-side polling of Splunk search results
      types.ts
  agent-mesh/                     # @splunk/agent-mesh — Splunk app bundle
    src/main/resources/splunk/
      default/agents.conf         # ← the mesh definition lives here
      default/collections.conf    # KV Store collection for durable investigations
      default/restmap.conf        # agent_mesh_bridge custom REST endpoint
      default/web.conf            # exposes the bridge under splunkd/__raw
      bin/agent_mesh_bridge.py    # Splunk-authenticated loopback proxy to uvicorn
      README/agents.conf.spec
      lookups/                    # Sample CSV data
server/
  agent_mesh/                     # Python FastAPI backend
    app.py                        # FastAPI routes + SSE streaming + delegated-auth checks
    config.py                     # Environment-based runtime configuration
    conf_reader.py                # SplunkRestConfReader + FileConfReader
    splunk_client.py              # Live Splunk search client (dispatch/poll/preview)
    job_store.py                  # In-memory investigation job manager + durable checkpointing
    durable_investigations.py     # KV Store persistence: records, repository, restore
    investigation_models.py       # Result-shape helpers + browser-safe projections
    request_context.py            # Per-request auth context (delegated session)
    security.py                   # Input validation (IDs, model names, URLs)
    stream_tokens.py              # Short-lived signed SSE stream tokens
    agents/
      agent_config.py             # AgentConfig dataclass
      events.py                   # Structured event schema + validator (pydantic)
      agentic_llm_agent.py        # Threat Hunter harness loop (the active agent)
      orchestrator.py             # Primary/sub-agent split, execution, artifact collection
    tools/splunk_search.py        # SPL execution, artifact shaping, viz inference
    llm/                          # Anthropic, OpenRouter, OpenAI-compatible
    demo/demo_case.py             # Paced Log4Shell replay (backend-side, no LLM call)
docs/
```

---

## Setup

The project supports **three deployment options**. The Docker container is the
easiest way to get a fully working demo with Splunk and sample data. The
bootstrap script offers two tiers: Tier 1 (demo, no Splunk) and Tier 2
(full/live, existing Splunk instance).

### Quick start — Docker (recommended for demos)

Run a self-contained Splunk + Agent Mesh instance with pre-loaded sample data:

```bash
git clone <repo> && cd splunk-agent-mesh
docker build -t splunk-agent-mesh .
docker run -d -p 8000:8000 -p 8765:8765 \
  -e SPLUNK_PASSWORD=changeme123 \
  --name agent-mesh splunk-agent-mesh
docker logs -f agent-mesh   # wait for "Splunk Agent Mesh is ready!" banner
```

Once the ready banner appears:

1. Open **http://localhost:8000/en-US/app/splunk-agent-mesh/Investigations**
2. Log in with `admin` / `changeme123` (or whatever you set `SPLUNK_PASSWORD` to)
3. Click the **gear icon** and enter your Anthropic API key
4. Start an investigation — or click **"Run Demo Investigation"** to try it without a key

The container automatically builds the frontend, installs the Splunk app,
creates demo indexes, and ingests all sample data on first boot. First startup
takes a couple of minutes while Splunk provisions.

### Quick start — Tier 1 demo (no Splunk, no LLM key)

From a clean checkout (macOS/Linux):

```bash
./scripts/bootstrap.sh
```

This preflights prerequisites (Node >= 22, Yarn, Python >= 3.11, curl), creates
a backend venv, starts uvicorn on `:8765` and a standalone UI on `:8080`, and
prints the URL. Open `http://localhost:8080` and click **"Run Demo
Investigation"** — the backend replays a paced Log4Shell scenario with canned
events and a chart artifact. No Splunk, LLM key, or tokens required. Ctrl-C
stops everything.

### Quick start — Tier 2 full/live (existing Splunk + LLM)

```bash
export AGENT_MESH_API_KEY=<your-llm-provider-key>
export SPLUNK_HOME=/path/to/splunk
./scripts/bootstrap.sh full
```

This builds the Splunk app, links it into `$SPLUNK_HOME/etc/apps`, starts
uvicorn (with `SPLUNK_TOKEN` intentionally unset), and prints the Splunk Web
URL. After linking, **restart Splunk** so it loads the app and the
`agent_mesh_bridge` REST endpoint, then load sample data (the script prints the
SPL). Searches run as the analyst's own delegated Splunk session — no shared
admin token. See `scripts/README.md` and `docs/DEMO_RUNTIME.md`.

### Prerequisites
- Node.js >= 22
- Yarn >= 1.22
- Python >= 3.11
- A Splunk Enterprise instance (for live mode; demo mode works without it)

### Build the frontend

```bash
yarn install
yarn build
```

Live reload:
```bash
yarn start  # webpack --watch on @splunk/agent-mesh
```

### Run the backend

```bash
cd server
pip install -r requirements.txt
uvicorn agent_mesh.app:app --reload --port 8765
```

Backend at `http://localhost:8765`. OpenAPI docs at `http://localhost:8765/docs`.

Run the tests:
```bash
cd server && python -m pytest tests/                       # backend
yarn workspace @splunk/agent-mesh-ui run test              # frontend
```

### Credentials and environment variables

Each credential has a single purpose; none are inferred or silently coupled.

| Variable | Required | Purpose |
|---|---|---|
| `AGENT_MESH_API_KEY` | Tier 2 | LLM provider API key, read by `DevSettingsStore` |
| `SPLUNK_HOST` | Tier 2 | Splunk REST URL (default `https://localhost:8089`) |
| `SPLUNK_TOKEN` | Opt-in only | Service token for explicitly enabled features (see below) |
| `AGENT_MESH_SETTINGS_STORE` | Optional | `dev` (default) or `splunk` — selects LLM key storage backend |
| `AGENT_MESH_CONF_SOURCE` | Optional | `file` (default) or `splunk` — selects agent config source |
| `AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK` | Optional | Set `1` to allow `SPLUNK_TOKEN` as a search fallback when no delegated session is present |
| `AGENT_MESH_STREAM_TOKEN_TTL_SECONDS` | Optional | SSE stream-token lifetime in seconds (default `14400`) |
| `AGENT_MESH_DEV_MODE` | Optional | Set `1` to allow `DevSettingsStore` to persist keys to disk |
| `AGENT_MESH_LOG_LLM` | Optional | Set `1` to log full LLM request/response payloads (debugging only) |
| `AGENT_MESH_LOG_LEVEL` | Optional | Python log level (default `INFO`) |
| `AGENT_MESH_SPLUNK_APP_ID` | Optional | Splunk app name (default `splunk-agent-mesh`) |
| `AGENT_MESH_CORS_ORIGINS` | Optional | Comma-separated CORS origins (default includes `localhost:8000,8080,3000`) |

`SPLUNK_TOKEN` is **not** the primary credential. Its presence alone does not
enable any sidecar operation. Three features each require their own explicit
opt-in to use it:

- `AGENT_MESH_SETTINGS_STORE=splunk` — LLM key storage via Splunk Passwords API
- `AGENT_MESH_CONF_SOURCE=splunk` — agent config via Splunk REST
- `AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK=1` — search fallback when no
  delegated session is present

### Link into Splunk

```bash
yarn workspace @splunk/agent-mesh run link:app
# Splunk will pick up the new app on next restart
```

---

## Configure the mesh

Edit `packages/agent-mesh/src/main/resources/splunk/default/agents.conf`.
Each `[agent:<id>]` stanza is one agent. Today the shipping mesh is intentionally
focused on a single visible agent plus one internal sub-agent.

```ini
[agent:spl_hunter]
display_name = Threat Hunter
agent_mode = agentic
agent_role = primary
skills = splunk_search
max_iterations = 14
system_prompt = You are the Threat Hunter ... respond with VALID JSON ONLY ...
```

### Stanza fields

| Field | Required | Default | Notes |
|---|---|---|---|
| `system_prompt` | yes | — | Multi-line via `\` continuation |
| `display_name` | no | id | Name shown in the report |
| `description` | no | "" | Shown in agent listings |
| `order` | no | 100 | Execution order (lower first) |
| `enabled` | no | 1 | Disabled stanzas are excluded entirely |
| `agent_mode` | no | single_shot | Set `agentic` for a primary agent (the harness event loop). `single_shot` is just the default label for sub-agents. |
| `agent_role` | no | primary | `primary` (user-visible, must be `agentic`) or `subagent` (delegated via handoff) |
| `max_iterations` | no | 10 | Safety cap on agentic loop turns |
| `model` | no | claude-sonnet-4-6 | LLM model identifier |
| `temperature` | no | 0.2 | Sampling temperature |
| `max_tokens` | no | 2048 | Completion length cap |
| `skills` | no | "" | Comma-separated skills (currently: `splunk_search`) |

See `packages/agent-mesh/src/main/resources/splunk/README/agents.conf.spec`,
and `docs/AGENT_DESIGN.md` for the response contract and the shipping mesh.

---

## The response contract

The Threat Hunter must return **valid JSON only** — a single object with an
`events` array. Each event is `{type, title, text, payload}`:

| Type | Meaning |
|---|---|
| `narration` | High-level explanation of what it's doing |
| `splunk_search` | A proposed/executed SPL query (`payload.query`, `payload.type` viz hint) |
| `result_summary` | Summary of search or sub-agent results |
| `finding` | A security-relevant observation (structured fields in `payload`) |
| `handoff` | Delegate to the reporting sub-agent |
| `final` | The closing answer (`payload.summary`, `payload.recommended_actions`) |

The harness (`agents/events.py` + `agents/agentic_llm_agent.py`) validates the
JSON, tolerates an accidental ```` ```json ```` fence, and on any failure routes
the corrective message *"Remember to always respond with json."* and retries.
It executes at most one action per turn (the last `splunk_search` or `handoff`),
appends results to context, and calls the agent again until a `final` event.

`splunk_search` `payload.type` accepts `timechart | table | column | line | pie
| single` (`column` is an alias for `timechart`); the value drives the inline
chart in `ArtifactRenderer`.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/agents` | List user-visible (primary) agents |
| GET | `/api/v1/investigations` | List investigations for the authenticated user (merged in-memory + durable) |
| POST | `/api/v1/investigations/run` | Synchronous investigation (blocks until complete) |
| POST | `/api/v1/investigations/start` | Start async investigation; returns id + `stream_token` |
| GET | `/api/v1/investigations/{id}` | Get full investigation (in-memory, or restored from KV Store) |
| GET | `/api/v1/investigations/{id}/status` | Get investigation state summary |
| GET | `/api/v1/investigations/{id}/stream?stream_token=…` | SSE stream of progressive events |
| POST | `/api/v1/investigations/{id}/cancel` | Cancel a running investigation |
| GET / POST | `/api/v1/settings` | Get / save LLM provider config |
| POST | `/api/v1/settings/test` | Test LLM connection |
| DELETE | `/api/v1/settings/credentials` | Clear stored API key |

SSE events: `agent_order`, `agent_update`, `agent_complete`,
`investigation_complete`, `error`.

---

## Auth (live mode)

Live mode has two independent data planes. Understanding the split is key to
the security model.

### Browser-side: analyst's Splunk Web session

The browser fetches search result **rows** directly from Splunk Web's
`splunkd/__raw` proxy using the analyst's own Splunk Web cookie. The backend
never sees or proxies these rows — `public_artifact` strips them from API
responses. Demo artifacts keep their rows (no real search job).

### Backend-side: uvicorn credential modes

| Operation | Credential | How it gets there |
|---|---|---|
| Live investigation searches | Analyst's delegated Splunk session | `agent_mesh_bridge` forwards `X-Splunk-User` + `X-Splunk-Token` over loopback |
| Session validation | Same delegated session | Backend calls `/authentication/current-context` to confirm the session matches the requesting user |
| LLM calls | `AGENT_MESH_API_KEY` (env) | Read by `DevSettingsStore` (default) |
| Agent config reads | Local file (default) | `FileConfReader` reads `agents.conf` from the repo |
| KV Store checkpoints | Analyst's delegated session | Investigation records are written/read with the analyst's own session |
| SSE stream auth | Signed `stream_token` | Issued by `POST /start`, HMAC-signed, default 4h TTL |

Each uvicorn-side credential mode is **explicitly selected**, not inferred from
`SPLUNK_TOKEN` presence. See **Credentials and environment variables** above.

The `agent_mesh_bridge` REST endpoint runs inside Splunk Web and forwards
requests to uvicorn over loopback. **uvicorn must not be exposed beyond
loopback** — any client that can set `X-Splunk-User` / `X-Splunk-Token` headers
would be trusted. See `docs/SECURE_SETTINGS.md`.

---

## Demo Mode

No API key or Splunk connection required. Click **"Run Demo Investigation"**
in the Investigation tab.

The demo is **backend-side**: `server/agent_mesh/demo/demo_case.py` replays a
canned Threat Hunter event stream with pacing (default 1.1s per step, set via
`AGENT_MESH_DEMO_STEP_SECONDS`). Events stream over SSE exactly like a live
run — narration → search (pending → running → done) → finding → handoff →
final — plus one chart artifact with guaranteed rows. The UI renders the same
progressive transcript it shows for live investigations.

> **Scenario:** User `jsmith` opens a suspicious Office document →
> `winword.exe` spawns encoded PowerShell → rare domain contacted → finance
> file server accessed → 48 MB exfiltrated. (Log4Shell / CVE-2021-44228.)

The console shows a **"Demo data"** badge for demo runs.

---

## Load sample data into Splunk

```spl
| inputlookup endpoint_events.csv | collect index=endpoint
| inputlookup dns_events.csv      | collect index=dns
| inputlookup auth_events.csv     | collect index=auth
| inputlookup proxy_events.csv    | collect index=proxy
| inputlookup firewall_events.csv | collect index=firewall
```

CSVs live at `packages/agent-mesh/src/main/resources/splunk/lookups/`.

---

## Investigation History and Durable Sessions

Completed and in-progress investigations are checkpointed to a Splunk KV Store
collection (`agent_mesh_investigations`). A collapsible history sidebar lists
past investigations; clicking one restores it into the console. Investigations
are URL-addressable via `?id=<investigation_id>` — shareable links, browser
back/forward, and page refresh all restore the session.

- **Per-user visibility**: each user sees only their own investigations.
- **30-day retention**: records expire after 30 days (filtered client-side).
- **Artifact metadata only**: search SIDs and visualization hints are stored,
  not result rows. Restored artifacts show "Results not available — run the
  search in Splunk" for real searches; demo artifacts keep their rows.
- **In-memory + durable merge**: the list API merges running in-memory jobs with
  durable KV Store records, deduplicating by ID (in-memory wins).

See `docs/DURABLE_INVESTIGATIONS.md` for the record schema and checkpoint
timing.

---

## Known POC Limitations

These are explicit design boundaries for the current proof-of-concept:

- **Loopback-only deployment**: uvicorn must not be exposed beyond `127.0.0.1`.
  The `agent_mesh_bridge` trusts `X-Splunk-User` / `X-Splunk-Token` headers
  because they arrive over loopback from Splunk Web. Any external client that
  can set those headers would be implicitly trusted.
- **Ephemeral stream-token signing secret**: the HMAC secret for SSE stream
  tokens is generated per-process (`secrets.token_bytes(32)` at import time).
  A uvicorn restart invalidates all outstanding stream tokens. Acceptable for
  single-process POC; production would use a persisted or shared secret.
- **In-memory job state**: `InvestigationJobStore` holds running investigations
  in memory. A server restart loses in-flight runs. Completed investigations
  survive in KV Store. Stream resume for interrupted sessions is not implemented
  (REL-001 postponed).
- **Single-process assumption**: the stream-token secret and in-memory job store
  assume a single uvicorn worker. Multiple workers would need a shared secret
  and a distributed job store.
- **Per-user only, no RBAC**: investigation visibility is scoped to
  `owner.username`. There is no admin/global view, role-based access, or
  cross-user sharing.
- **No TLS termination**: uvicorn runs plain HTTP. TLS is expected from the
  reverse proxy (Splunk Web for Tier 2, or an external proxy for standalone).

---

## Architecture

See `docs/ARCHITECTURE.md` for the full design, `docs/DECISIONS.md` for ADRs,
`docs/AGENT_DESIGN.md` for the stanza + event-contract reference,
`docs/AGENTIC_ARCHITECTURE_REVIEW.md` for the agentic loop as built,
`docs/DURABLE_INVESTIGATIONS.md` for the KV Store persistence model, and
`docs/legacy/HISTORY.md` for how the project got here.
