# Splunk Agent Mesh

**A configurable agentic platform for Splunk Enterprise.**

Define a mesh of AI agents in `agents.conf`. Give the user request. Each agent
writes back to the page in markdown. The bundled "first mesh" is a SOC
investigation mesh, but the platform is general — add a stanza and a new agent
shows up as a new tab.

---

**Run the python agent server for testing.**

```
cd server/
python3 -m uvicorn agent_mesh.app:app --port 8765
```

---

## How it works

```
agents.conf  (Splunk app default + local)
     │
     ▼
SplunkRestConfReader  ──▶  Orchestrator  ──▶  LLMAgent × N  ──▶  markdown
                                                                     │
                                                                     ▼
                                                              Browser
                                                       (one tab per agent)
```

- Backend: FastAPI on port 8765. Reads `agents.conf` via Splunk REST.
- Each agent is fully described by its stanza (system prompt, model, order).
- The runtime ships one generic `LLMAgent` — no per-agent code.
- Agents are independent in v1 (each sees only the original user request).
- Outputs are sanitized markdown. The UI renders with `react-markdown`.

See `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` (ADR-006, 007, 008) for
the full design.

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
        MarkdownView.tsx          # Sanitized markdown + pluggable code-block renderers
        AgentTabsPanel.tsx        # Dynamic tabs from the configured mesh
        AgentStatusBadge.tsx
        legacy/                   # Archived structured-output components
      services/apiClient.ts
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
    conf_reader.py                # SplunkRestConfReader + FileConfReader
    agents/
      agent_config.py             # AgentConfig dataclass
      llm_agent.py                # Generic LLM-backed agent
      orchestrator.py
    llm/                          # Anthropic, OpenRouter, OpenAI-compatible
    demo/demo_case.py
    app.py
docs/
splunk/                           # Example SPL and conf snippets
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

### Link into Splunk

```bash
yarn workspace @splunk/agent-mesh run link:app
# Splunk will pick up the new app on next restart
```

---

## Configure the mesh

Edit `packages/agent-mesh/src/main/resources/splunk/default/agents.conf`.

Each `[agent:<id>]` stanza becomes one tab in the UI and one node in the
orchestrator's run loop.

```ini
[agent:my_agent]
display_name = My Agent
description = Does something useful.
order = 100
system_prompt = You are <role>. Given <input>, respond in markdown with \
  sections: ## Section A, ## Section B. \
  Be concise.
```

See `docs/AGENT_DESIGN.md` for the full stanza reference and
`packages/agent-mesh/src/main/resources/splunk/README/agents.conf.spec` for the
Splunk-style spec.

Reload conf:
```bash
splunk reload deploy-server
# or via Splunk Web: Settings → Server controls → Restart
```

Refresh the page in Splunk Web — new tabs appear.

---

## Configure the LLM provider

1. Open Splunk Agent Mesh in Splunk Web.
2. Click the **Settings** tab.
3. Pick a provider (Anthropic, OpenRouter, OpenAI-compatible).
4. Enter the model name and API key.
5. Click **Save**, then **Test Connection**.

For local dev only:
```bash
export AGENT_MESH_API_KEY=...
export AGENT_MESH_DEV_MODE=1   # required to persist a key to disk
```

API keys are never returned to the browser. The Settings page shows only
`api_key_configured: true|false`.

| Environment | Storage |
|---|---|
| Splunk Enterprise | Splunk Passwords API (encrypted at rest) — Phase 3.1 |
| Local dev | `AGENT_MESH_API_KEY` env var |
| Explicit dev persistence | `.agent_mesh_settings.json` (gitignored) |

---

## Demo Mode

No API key or Splunk connection required. Click **Load Suspicious PowerShell
Demo** in the Investigation tab.

The demo populates every configured agent's tab with canned markdown that
matches the scenario:

> User `jsmith` opens a suspicious Office document → `winword.exe` spawns
> encoded PowerShell → rare domain contacted → finance file server accessed
> → 48 MB exfiltrated.

If you add a new agent stanza without a canned demo block, the demo shows a
"no demo content for this agent" placeholder so no tab silently disappears.

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

## Known Limitations (MVP)

- LLM providers wired but not live-tested end-to-end yet.
- `SplunkSecureSettingsStore` (Passwords API) and `SplunkClient` (search jobs)
  are stubs awaiting Phase 3.
- Agents run sequentially server-side. Streaming and parallel execution are
  deferred (see `docs/TODO.md`).
- Skills (tool use) are reserved in the stanza format but not implemented.

---

## Continuation Notes

`docs/CONTINUATION_LOG.md` tracks session-by-session change history. Every
coding session must append an entry to that file.

---

## Original Scaffold Notes

This project was created with Splunk Create / `@splunk/create`. It is a Yarn
workspace monorepo.

- `yarn run setup` — install deps and build all packages
- `yarn run build` — production bundle
- `yarn run test` — unit tests
- `yarn run lint` — JS + CSS linting
- `yarn run format` — auto-format with Prettier
