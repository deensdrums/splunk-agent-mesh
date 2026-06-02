# Splunk Agent Mesh

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

- **Backend**: FastAPI on port 8765. Reads `agents.conf` via Splunk REST.
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
        EventRenderer.tsx         # Renders one structured event (colored accent blocks)
        ArtifactRenderer.tsx      # Search results → Column/Line/Pie/Bar/Table/Single
        MarkdownView.tsx          # Sanitized markdown (final-summary / legacy fallback)
        AgentStatusBadge.tsx
        legacy/                   # Archived structured-output components (unused)
      hooks/useStaggeredReveal.ts # Reveal events one at a time
      services/
        apiClient.ts              # HTTP + SSE client (routes via Splunk bridge in Web)
        splunkWeb.ts              # Splunk Web runtime detection + REST URL helper
        splunkSearchResults.ts    # Browser-side polling of Splunk search results
      demo/demoData.ts            # Canned Threat Hunter event stream for offline demo
      types.ts
  agent-mesh/                     # @splunk/agent-mesh — Splunk app bundle
    src/main/resources/splunk/
      default/agents.conf         # ← the mesh definition lives here
      default/restmap.conf        # agent_mesh_bridge custom REST endpoint
      default/web.conf            # exposes the bridge under splunkd/__raw
      bin/agent_mesh_bridge.py    # Splunk-authenticated loopback proxy to uvicorn
      README/agents.conf.spec
      lookups/                    # Sample CSV data
server/
  agent_mesh/                     # Python FastAPI backend
    app.py                        # FastAPI routes + SSE streaming + delegated-auth checks
    conf_reader.py                # SplunkRestConfReader + FileConfReader
    splunk_client.py              # Live Splunk search client (dispatch/poll/preview)
    job_store.py                  # Async investigation job manager
    investigation_models.py       # Result-shape helpers + browser-safe projections
    request_context.py            # Per-request auth context (delegated session)
    stream_tokens.py              # Short-lived signed SSE stream tokens
    agents/
      agent_config.py             # AgentConfig dataclass
      events.py                   # Structured event schema + validator (pydantic)
      agentic_llm_agent.py        # Threat Hunter harness loop (the active agent)
      orchestrator.py             # Primary/sub-agent split, execution, artifact collection
    tools/splunk_search.py        # SPL execution, artifact shaping, viz inference
    llm/                          # Anthropic, OpenRouter, OpenAI-compatible
    demo/demo_case.py             # Canned Threat Hunter event stream + artifact
docs/
```

---

## Setup

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

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `AGENT_MESH_API_KEY` | For LLM calls | LLM API key read by the dev settings store |
| `AGENT_MESH_DEV_MODE` | Optional | Set `1` to allow plaintext key persistence |
| `SPLUNK_HOST` | For live mode | Splunk REST URL (default: `https://localhost:8089`) |
| `SPLUNK_TOKEN` | Optional | Service token for explicitly enabled sidecar Splunk REST operations |
| `AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK` | Optional | Set `1` to allow live runs to use `SPLUNK_TOKEN` when no delegated session is present |
| `AGENT_MESH_STREAM_TOKEN_TTL_SECONDS` | Optional | SSE stream-token lifetime (default `14400`) |
| `AGENT_MESH_LOG_LLM` | Optional | Set `1` to log full LLM requests/responses (debugging) |
| `AGENT_MESH_SETTINGS_STORE` | Optional | LLM key storage: `dev` (default) or `splunk` |
| `AGENT_MESH_CONF_SOURCE` | Optional | Agent config source: `file` (default) or `splunk` |

In production the analyst's own Splunk session is delegated per request
(see **Auth** below); `SPLUNK_TOKEN` is not the primary credential and its
presence alone does not enable any sidecar Splunk REST operation.

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
| POST | `/api/v1/investigations/run` | Synchronous investigation (blocks until complete) |
| POST | `/api/v1/investigations/start` | Start async investigation; returns id + `stream_token` |
| GET | `/api/v1/investigations/{id}/status` | Get investigation state |
| GET | `/api/v1/investigations/{id}/stream?stream_token=…` | SSE stream of progressive events |
| POST | `/api/v1/investigations/{id}/cancel` | Cancel a running investigation |
| GET / POST | `/api/v1/settings` | Get / save LLM provider config |
| POST | `/api/v1/settings/test` | Test LLM connection |
| DELETE | `/api/v1/settings/credentials` | Clear stored API key |

SSE events: `agent_order`, `agent_update`, `agent_complete`,
`investigation_complete`, `error`.

---

## Auth (live mode)

Inside Splunk Web the React app calls the **`agent_mesh_bridge`** custom REST
endpoint, which forwards the request to uvicorn with the analyst's Splunk
username and session key. The backend validates that session
(`/authentication/current-context`) and runs all searches as that user — no
shared admin token. The SSE stream connects directly to uvicorn, gated by a
short-lived signed `stream_token` from `/start`.

Search rows are **not** returned by the JSON API; the browser fetches them
itself from Splunk Web's authenticated `splunkd/__raw` proxy (demo artifacts
keep their rows). See `docs/ARCHITECTURE.md` and `docs/SECURE_SETTINGS.md`.

---

## Demo Mode

No API key or Splunk connection required. Click **Load Suspicious PowerShell
Demo** in the Investigation tab. The backend returns a canned Threat Hunter
**event stream** (narration → search → finding → handoff → final) plus one
search artifact, mirroring the live wire shape:

> User `jsmith` opens a suspicious Office document → `winword.exe` spawns
> encoded PowerShell → rare domain contacted → finance file server accessed
> → 48 MB exfiltrated.

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

## Architecture

See `docs/ARCHITECTURE.md` for the full design, `docs/DECISIONS.md` for ADRs,
`docs/AGENT_DESIGN.md` for the stanza + event-contract reference,
`docs/AGENTIC_ARCHITECTURE_REVIEW.md` for the agentic loop as built, and
`docs/legacy/HISTORY.md` for how the project got here.
