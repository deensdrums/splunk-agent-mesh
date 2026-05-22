# Splunk Agent Mesh

**From alert to evidence-backed response in minutes.**

Splunk Agent Mesh is an agentic SOC investigation copilot for Splunk. A SOC analyst describes an alert, clicks **Start Investigation**, and receives an evidence-backed report with MITRE ATT&CK mapping, blast radius analysis, response recommendations, and a reusable detection rule — powered by AI agents running against Splunk security data.

---

## Hackathon Track

Security — Splunk Agentic Ops Hackathon 2026

---

## Architecture

```
Browser (Splunk Web)
  └── @splunk/agent-mesh  (Splunk app, single React page)
        └── @splunk/agent-mesh-ui  (React component library)
              ├── InvestigationPage  (main SOC console)
              ├── SettingsPage       (LLM provider + secure API key)
              └── AboutPage

FastAPI backend (server/agent_mesh/)
  ├── Orchestrator → 7 specialized agents
  ├── LLM providers (Anthropic / OpenRouter / OpenAI-compatible)
  ├── Splunk search client
  └── SettingsStore (dev: env var | production: Splunk Passwords API)
```

See `docs/ARCHITECTURE.md` for the full data flow diagram.

---

## Setup

### Prerequisites
- Node.js >= 22
- Yarn >= 1.2
- Python >= 3.11

### Frontend

```bash
yarn install
yarn build
```

To develop with live reload:
```bash
yarn start    # runs webpack --watch on the splunk-agent-mesh package
```

### Backend

```bash
cd server
pip install -r requirements.txt
uvicorn agent_mesh.app:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

---

## Configure LLM Provider

1. Open the Splunk Agent Mesh app in Splunk Web.
2. Click the **Settings** tab.
3. Select your LLM provider (Anthropic, OpenRouter, or custom).
4. Enter your model name and API key.
5. Click **Save**, then **Test Connection**.

For local development only, you can also set:
```bash
export AGENT_MESH_API_KEY=your-key-here
export AGENT_MESH_DEV_MODE=1   # allows local key persistence
```

**API keys are never stored in plaintext in the repo.** See `docs/SECURE_SETTINGS.md`.

---

## Credential Storage

| Environment | Storage |
|---|---|
| Production (Splunk) | Splunk Passwords API (encrypted at rest) |
| Local dev | `AGENT_MESH_API_KEY` env var |
| Dev mode (explicit) | `.agent_mesh_settings.json` (gitignored) |

The API key is never returned to the frontend. Settings responses show only `api_key_configured: true/false`.

---

## Demo Mode

No API key or Splunk connection needed. Click **"Load Suspicious PowerShell Demo"** in the Investigation tab to run the built-in synthetic scenario:

> User `jsmith` opens a suspicious Office document → `winword.exe` spawns encoded PowerShell → rare domain contacted → finance file server accessed → 48 MB exfiltrated.

The demo returns a deterministic result showing the full investigation workflow.

---

## Load Sample Data into Splunk

Sample event CSVs are in `packages/splunk-agent-mesh/src/main/resources/splunk/lookups/`.

To index them:
```splunk
| inputlookup endpoint_events.csv | collect index=endpoint
| inputlookup dns_events.csv | collect index=dns
| inputlookup auth_events.csv | collect index=wineventlog
| inputlookup proxy_events.csv | collect index=proxy
| inputlookup firewall_events.csv | collect index=firewall
```

---

## Repo Structure

```
packages/
  investigations/        # React component library (@splunk/agent-mesh-ui)
    src/
      pages/             # InvestigationPage, SettingsPage, AboutPage
      components/        # AgentRunPanel, Timeline, Evidence, etc.
      services/          # apiClient.ts
      demo/              # demoData.ts (static demo result)
      types.ts           # TypeScript types
  splunk-agent-mesh/       # Splunk app (@splunk/agent-mesh)
    src/main/
      webapp/pages/      # Webpack entry points
      resources/splunk/  # Splunk app config, nav, views, lookups
server/
  agent_mesh/         # Python FastAPI backend
    agents/              # 7 investigation agents
    llm/                 # LLM provider adapters
    demo/                # Static demo case + synthetic events
    app.py               # FastAPI routes
    settings_store.py    # Credential storage abstraction
docs/                    # Project planning and architecture
splunk/
  spl/                   # Example SPL detection queries
  config_examples/       # Splunk conf file examples
```

---

## Known Limitations (MVP)

- Demo mode only — real Splunk search integration requires a live Splunk instance and `SPLUNK_TOKEN` env var
- LLM agents are deterministic stubs — LLM integration is wired but requires a configured API key and installed provider packages (`pip install anthropic` or `pip install openai`)
- `SplunkSecureSettingsStore` methods are stubs — full Passwords API wiring is a next-session task
- No investigation history — each run is stateless
- Entity graph is a placeholder (D3/Cytoscape visualization planned for v2)

---

## Next Steps

See `docs/TODO.md` for the full backlog. Immediate priorities:
1. `yarn build` — verify frontend compiles with no TypeScript errors
2. `uvicorn agent_mesh.app:app --reload` — verify backend starts
3. Test the demo endpoint: `curl -X POST http://localhost:8000/api/v1/investigations/run -d '{"description":"test","demo":true}' -H 'Content-Type: application/json'`
4. Wire `SplunkSecureSettingsStore` to real Splunk Passwords API
5. Connect `splunk_client.py` to a real Splunk instance

---

## Continuation Notes

See `docs/CONTINUATION_LOG.md` for session-by-session change history. Every coding session must append an entry to that file.

---

## Original Scaffold Notes

This project was created with Splunk Create / `@splunk/create`. It is a Yarn workspace monorepo. Original scaffold README is preserved below.

### Yarn Workspaces

Use [Yarn Workspaces](https://yarnpkg.com/lang/en/docs/workspaces/) to manage packages.

- `yarn run setup` — install deps and build all packages
- `yarn run build` — production bundle
- `yarn run test` — unit tests
- `yarn run lint` — JS + CSS linting
- `yarn run format` — auto-format with Prettier
