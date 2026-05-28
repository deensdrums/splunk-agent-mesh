# Splunk Agent Mesh

**A configurable agentic platform for Splunk Enterprise.**

Define a mesh of AI agents in `agents.conf`. Give the user request. Each agent
writes back to the page in markdown, and agents with the `splunk_search` skill
execute SPL queries against live Splunk data — results render as interactive
charts and tables inline in the report.

---

## How it works

```
agents.conf  (Splunk app default + local)
     │
     ▼
SplunkRestConfReader  ──▶  Orchestrator  ──▶  LLMAgent × N  ──▶  markdown + artifacts
                               │                                       │
                               │  depends_on edges                     ▼
                               │  (DAG execution)              InvestigationReport
                               │                               (sections + charts)
                               ▼
                        SSE stream to browser
                        (progressive rendering)
```

- **Backend**: FastAPI on port 8765. Reads `agents.conf` via Splunk REST.
- Each agent is fully described by its stanza (system prompt, model, order, skills, dependencies).
- The runtime ships one generic `LLMAgent` — no per-agent code.
- Agents with `depends_on` receive prior agents' markdown and artifact metadata as context.
- Agents with `skills = splunk_search` emit fenced SPL blocks; the orchestrator executes them against Splunk and attaches results as structured artifacts.
- The UI renders progressively via SSE — each agent's section appears as it completes.

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
        InvestigationReport.tsx   # Report layout — sections per agent + artifacts
        ArtifactRenderer.tsx      # Renders search results as charts/tables
        MarkdownView.tsx          # Sanitized markdown rendering
        AgentStatusBadge.tsx
        legacy/                   # Archived structured-output components
      services/apiClient.ts       # HTTP + SSE streaming client
      demo/demoData.ts
      types.ts
  agent-mesh/                     # @splunk/agent-mesh — Splunk app bundle
    src/main/
      webapp/pages/Investigations # Webpack entry
      resources/splunk/
        default/agents.conf       # ← the mesh definition lives here
        default/app.conf, nav, views
        README/agents.conf.spec
        lookups/                  # Sample CSV data
server/
  agent_mesh/                     # Python FastAPI backend
    app.py                        # FastAPI routes + SSE streaming
    conf_reader.py                # SplunkRestConfReader + FileConfReader
    splunk_client.py              # Live Splunk search client
    job_store.py                  # Async investigation job manager
    investigation_models.py       # Shared result shape helpers
    request_context.py            # Per-request auth context
    agents/
      agent_config.py             # AgentConfig dataclass
      llm_agent.py                # Generic LLM-backed agent
      orchestrator.py             # DAG execution, skill dispatch, artifact collection
    tools/
      splunk_search.py            # SPL extraction, execution, visualization inference
    llm/                          # Anthropic, OpenRouter, OpenAI-compatible
    demo/demo_case.py
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

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `SPLUNK_TOKEN` | For live mode | Splunk admin bearer token |
| `SPLUNK_HOST` | For live mode | Splunk REST URL (default: `https://localhost:8089`) |
| `AGENT_MESH_API_KEY` | For LLM calls | Anthropic/OpenRouter API key |
| `AGENT_MESH_DEV_MODE` | Optional | Set `1` to allow plaintext key persistence |

### Link into Splunk

```bash
yarn workspace @splunk/agent-mesh run link:app
# Splunk will pick up the new app on next restart
```

---

## Configure the mesh

Edit `packages/agent-mesh/src/main/resources/splunk/default/agents.conf`.

Each `[agent:<id>]` stanza becomes one section in the investigation report and
one node in the orchestrator's execution DAG.

```ini
[agent:my_agent]
display_name = My Agent
description = Does something useful.
order = 100
skills = splunk_search
depends_on = triage
system_prompt = You are <role>. Given <input>, respond in markdown with \
  sections: ## Section A, ## Section B. \
  Use ```spl_table for search results. \
  Be concise.
```

### Stanza fields

| Field | Required | Default | Notes |
|---|---|---|---|
| `system_prompt` | yes | — | Multi-line via `\` continuation |
| `display_name` | no | id | Section heading in the report |
| `description` | no | "" | Shown in agent listings |
| `order` | no | 100 | Execution order (lower first) |
| `enabled` | no | 1 | Disabled agents are excluded |
| `model` | no | claude-sonnet-4-6 | LLM model identifier |
| `temperature` | no | 0.2 | Sampling temperature |
| `max_tokens` | no | 2048 | Completion length cap |
| `skills` | no | "" | Comma-separated skill names (currently: `splunk_search`) |
| `depends_on` | no | "" | Comma-separated agent ids that must complete first |

See `packages/agent-mesh/src/main/resources/splunk/README/agents.conf.spec`.

Reload conf:
```bash
splunk reload deploy-server
# or via Splunk Web: Settings → Server controls → Restart
```

---

## Skills

### `splunk_search`

Agents with `skills = splunk_search` can emit fenced SPL blocks in their
markdown output. The orchestrator extracts these blocks, executes them against
Splunk via the search jobs API, and attaches the results as structured artifacts
with inferred visualizations.

**Visualization hints**: Agents specify chart type via the fence tag suffix:

| Fence tag | Visualization |
|---|---|
| ` ```spl_column ` | Column chart (timechart data) |
| ` ```spl_line ` | Line chart (trends) |
| ` ```spl_bar ` | Bar chart (categorical) |
| ` ```spl_pie ` | Pie chart (proportional) |
| ` ```spl_single ` | Single numeric value |
| ` ```spl_table ` | Data table |
| ` ```spl ` | Auto-inferred from data shape (fallback) |

The frontend renders artifacts using `@splunk/visualizations` (Column, Line, Pie)
for chart types and a native HTML table for tabular data.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/agents` | List configured agents |
| POST | `/api/v1/investigations/run` | Synchronous investigation (blocks until complete) |
| POST | `/api/v1/investigations/start` | Start async investigation (returns immediately) |
| GET | `/api/v1/investigations/{id}/status` | Get investigation state |
| GET | `/api/v1/investigations/{id}/stream` | SSE stream of progressive results |
| POST | `/api/v1/investigations/{id}/cancel` | Cancel a running investigation |
| GET | `/api/v1/settings` | Get LLM provider config |
| POST | `/api/v1/settings` | Save LLM provider config |
| POST | `/api/v1/settings/test` | Test LLM connection |
| DELETE | `/api/v1/settings/credentials` | Clear stored API key |

---

## Demo Mode

No API key or Splunk connection required. Click **Load Suspicious PowerShell
Demo** in the Investigation tab.

The demo populates every configured agent's section with canned markdown that
matches the scenario:

> User `jsmith` opens a suspicious Office document → `winword.exe` spawns
> encoded PowerShell → rare domain contacted → finance file server accessed
> → 48 MB exfiltrated.

---

## Load sample data into Splunk

```spl
| inputlookup endpoint_events.csv | collect index=endpoint
| inputlookup dns_events.csv | collect index=dns
| inputlookup auth_events.csv | collect index=wineventlog
| inputlookup proxy_events.csv | collect index=proxy
| inputlookup firewall_events.csv | collect index=firewall
```

CSVs live at `packages/agent-mesh/src/main/resources/splunk/lookups/`.

---

## Architecture

See `docs/ARCHITECTURE.md` for the full design, `docs/DECISIONS.md` for ADRs,
and `docs/AGENT_DESIGN.md` for the stanza reference and default SOC mesh
documentation.
