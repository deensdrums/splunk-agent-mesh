# Splunk Agent Mesh — Continuation Log

This file orients the next working session on the **current** state. The full
historical narrative (how the project evolved) lives in
`docs/legacy/HISTORY.md`. Append a brief entry here when the current-state
picture changes materially.

---

## Current state — 2026-06-01

### What this is
An agentic SOC investigation copilot. One user-visible **Threat Hunter** agent
investigates an alert by returning a structured JSON **event stream**; a harness
validates each response, runs one action per turn against live Splunk, and
streams results to a console-style UI.

### Architecture in one paragraph
`agents.conf` → `ConfReader` → `Orchestrator` runs the primary agent
(`spl_hunter`, "Threat Hunter", `agent_mode = agentic`) through
`AgenticLLMAgent`. The agent emits `{events:[...]}`; `agents/events.py`
validates it. The harness executes the last `splunk_search` (live Splunk via the
analyst's delegated session) or `handoff` (the `executive_brief` "Reporting"
sub-agent), feeds results back, and ends on `final`. Events + artifacts stream
over SSE; the browser fetches search rows directly from Splunk Web. See
`docs/ARCHITECTURE.md`.

### Where things live
- Event schema/validator: `server/agent_mesh/agents/events.py`
- Harness loop: `server/agent_mesh/agents/agentic_llm_agent.py`
- Orchestrator (primary/subagent split): `server/agent_mesh/agents/orchestrator.py`
- Search execution: `server/agent_mesh/tools/splunk_search.py`, `splunk_client.py`
- Auth / streaming: `app.py`, `request_context.py`, `stream_tokens.py`,
  and the Splunk bridge under `packages/agent-mesh/.../bin/agent_mesh_bridge.py`
- UI: `packages/agent-mesh-ui/src/components/{InvestigationReport,EventRenderer,ArtifactRenderer}.tsx`,
  `pages/InvestigationPage.tsx`, `services/{apiClient,splunkWeb,splunkSearchResults}.ts`
- Mesh definition: `packages/agent-mesh/src/main/resources/splunk/default/agents.conf`

### Shipping mesh
- `spl_hunter` — primary, agentic, `skills = splunk_search`, `max_iterations = 14`.
- `executive_brief` — `agent_role = subagent` ("Reporting"), invoked via handoff.
- `triage`, `timeline`, `blast_radius`, `detection_gap`, `response` — `enabled = 0`.

### How to run / test
```bash
# backend
cd server && pip install -r requirements.txt
uvicorn agent_mesh.app:app --reload --port 8765
python -m pytest tests/

# frontend
yarn install && yarn build
yarn workspace @splunk/agent-mesh-ui run test
yarn workspace @splunk/agent-mesh-ui run types:build
yarn workspace @splunk/agent-mesh-ui run lint
```
Demo (no LLM/Splunk): `POST /api/v1/investigations/run` with `{"demo": true}` —
returns a canned Threat Hunter event stream + one artifact.

### Status / known gaps
- Tests green at last check: backend 30, frontend 20.
- Single-process assumptions: in-memory job store; per-process SSE stream-token
  secret (tokens don't survive a restart). Fine for the laptop POC.
- `DevSettingsStore` is the default. `SplunkSecureSettingsStore` makes real
  Passwords API calls only when `AGENT_MESH_SETTINGS_STORE=splunk` is selected.
- `AgentTabsPanel` / `legacy/` components are unused and slated for removal.

### Conventions
- Work on a feature branch and merge to `main` via PR (do not commit to `main`
  directly).
- Keep docs current: this file for current-state, `docs/legacy/HISTORY.md` for
  the evolution narrative, `docs/DECISIONS.md` for ADRs.
