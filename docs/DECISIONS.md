# Splunk Agent Mesh — Architecture Decisions

---

## ADR-001: Backend as FastAPI Service (not Splunk REST Handler)

**Date**: 2026-05-18  
**Status**: Accepted

**Context**: The Splunk Create scaffold provides a React app with a Splunk app wrapper. A backend is needed to run agent orchestration and LLM calls. Options are:
1. Splunk Custom REST Handler (Python, runs inside Splunk process)
2. Standalone FastAPI service (Python, runs outside Splunk)
3. No backend — pure frontend with direct LLM calls

**Options Considered**:
- **Splunk REST Handler**: Pro: fully integrated, deploys with app. Con: Python environment is managed by Splunk, harder to install dependencies (anthropic SDK etc.), slower iteration, no async support in older Splunk Pythons.
- **FastAPI standalone**: Pro: fast development, full async, easy dependency management, easy local testing. Con: requires separate deployment step; not automatically part of Splunk app bundle.
- **Frontend-only LLM calls**: Pro: simplest. Con: API keys would be exposed to browser. Hard non-starter per security requirements.

**Chosen Approach**: FastAPI standalone service (`server/agent_mesh/`). For Splunk production packaging, the same Python logic will be wrapped in a Splunk Custom REST Handler in a future session.

**Consequences**:
- Local dev requires running `uvicorn agent_mesh.app:app --port 8765` separately.
- The Splunk app React code calls `http://localhost:8765` (configurable via `window.__AGENT_MESH_API_URL__`) in dev, and will call the Splunk REST proxy in production.
- Backend dependencies go in `server/requirements.txt`, not in the Splunk app.

---

## ADR-002: Single-Page Tab Navigation (not React Router)

**Date**: 2026-05-18  
**Status**: Accepted

**Context**: The app needs three views: Investigation, Settings, About. React Router is the standard choice for SPAs, but Splunk Web has its own URL management and the app runs inside an iframe-like context where hash routing can behave unexpectedly.

**Options Considered**:
- **React Router (HashRouter)**: Works in Splunk, but adds dependency complexity and may conflict with Splunk's own URL manipulation.
- **React Router (BrowserRouter)**: Requires server-side routing support — not available in this Splunk app context.
- **Tab-based navigation with useState**: Simple, zero dependencies, no URL complexity, works perfectly inside Splunk Web.
- **Multiple Splunk views**: Each page is a separate Splunk view (separate webpack bundle). More "Splunk native" but requires more wiring, HTML templates, and XML view files.

**Chosen Approach**: Tab-based navigation via `useState` in the root `Investigations` component. Single webpack bundle. Navigation bar implemented with `@splunk/react-ui` Tab components.

**Consequences**:
- No URL-based deep linking to Settings or About in MVP.
- Simpler build: single webpack entry point.
- Can be upgraded to multiple Splunk views later by extracting each tab into a separate page directory.

---

## ADR-003: SettingsStore Abstraction with DevMode Guard

**Date**: 2026-05-18  
**Status**: Accepted

**Context**: API keys must never be stored in plaintext in the repo or in browser storage. The Splunk Passwords API is the right long-term solution but requires a running Splunk instance with the app installed. During development, some fallback is needed.

**Chosen Approach**: Abstract `SettingsStore` with two implementations:
1. `SplunkSecureSettingsStore` — production, uses Splunk Passwords API
2. `DevSettingsStore` — local dev, reads from `AGENT_MESH_API_KEY` env var. Refuses to store plaintext to disk unless `AGENT_MESH_DEV_MODE=1` is explicitly set.

**Consequences**:
- Developers must set `AGENT_MESH_API_KEY` env var locally (not commit it).
- No accidental plaintext key storage.
- Clear upgrade path to production.

---

## ADR-004: Deterministic Demo Mode

**Date**: 2026-05-18  
**Status**: Accepted

**Context**: For the hackathon demo, a live Splunk instance and live LLM API may not be available or reliable. A deterministic demo ensures the demo always works.

**Chosen Approach**: `POST /api/v1/investigations/run` accepts a `demo: true` flag. When set, the orchestrator returns the static `demo_case.py` result immediately without any agent invocations, Splunk calls, or LLM calls. The frontend "Load Demo" button sets this flag.

**Consequences**:
- Demo is always reliable.
- No API key needed for demo.
- Clear separation: demo mode vs. real mode.

---

## ADR-005: React Component Library in Separate Package

**Date**: 2026-05-18 (pre-existing scaffold decision)  
**Status**: Accepted (inherited)

**Context**: The Splunk Create scaffold created two packages: `@splunk/agent-mesh-ui` (component library) and `@splunk/agent-mesh` (Splunk app). All React UI logic lives in the UI library. The Splunk app imports from it.

**Consequences**:
- UI changes go in `packages/agent-mesh-ui/src/`.
- Splunk app pages (`packages/agent-mesh/src/main/webapp/pages/`) are thin entry points only.
- This is a clean separation that allows the component library to be tested standalone (via `start:demo`).

---

## ADR-006: Agents as Configuration, not Code

**Date**: 2026-05-21
**Status**: Accepted

**Context**: The original 7 agents were each implemented as a Python class with hardcoded prompts, MITRE maps, SPL templates, and severity heuristics. Adding a new agent meant writing a new file. Tuning a prompt meant a code change. The product is meant to be a *platform* — adding or tuning agents must not require code edits.

**Options Considered**:
- **Keep agent classes, externalize prompts only**: Cheap, but still hardcodes the agent set in Python. Adding an agent stays code-heavy.
- **YAML/JSON config files**: Easy to parse, but foreign to Splunk admins.
- **`agents.conf` (Splunk conf format)**: Native to Splunk operators, supports `[default]` inheritance, integrates with the Splunk REST configs API and `local/` override conventions, can be bundled with the app and edited via Splunk Web.

**Chosen Approach**: One generic `LLMAgent` class. Each agent is fully described by an `[agent:<id>]` stanza in `default/agents.conf`: display name, description, system prompt, model, temperature, order. The backend reads the conf via the Splunk REST API in production (`SplunkRestConfReader`) and falls back to direct file parsing for unit tests and dev (`FileConfReader`).

**Consequences**:
- Adding an agent = adding a stanza. No backend redeploy needed.
- Tuning a prompt = editing a value. Reloadable via Splunk's standard conf reload.
- The Python code knows nothing about specific SOC concepts (MITRE, SPL, triage) — those live in the prompts.
- Reserved future fields (`skills`, `output_format=json|mixed`) leave room without re-opening the contract.

---

## ADR-007: Agents Are Independent in v1

**Date**: 2026-05-21
**Status**: Accepted

**Context**: A natural design for multi-agent systems chains agents together — each one reads prior outputs and refines them. That creates coupling: one agent's output schema becomes another's input contract; a prompt change in agent N can break agent N+1.

**Chosen Approach**: In v1, each agent receives only the original user request. Agents do not see each other's outputs. The orchestrator collects all per-agent markdown into a flat `agents: Record<string, AgentOutput>` and the UI displays each in its own tab. The user is the integrator.

**Consequences**:
- Agents are trivially parallelizable (deferred — sequential is fine for v1).
- Tuning one agent never breaks another.
- No emergent reasoning across agents — that's a deliberate v1 limitation.
- A future ADR can add explicit `depends_on = ` if cross-agent context becomes desirable; the current shape is forward-compatible.

---

## ADR-008: Markdown as the Agent Output Lingua Franca

**Date**: 2026-05-21
**Status**: Accepted

**Context**: Agent outputs need to render in the UI. Choices:
- Strongly-typed JSON shapes per agent — high fidelity, brittle, requires UI work for every new agent.
- Free text — easy, ugly.
- Markdown — readable, supports tables/code/links, sanitizable, can be progressively enriched.

**Chosen Approach**: All agents emit GitHub-flavored markdown. The UI renders with `react-markdown` + `remark-gfm` + `rehype-sanitize`. The `MarkdownView` component accepts a `codeBlockRenderers` registry keyed by language tag — empty in v1, populated later as skills produce structured blocks (` ```spl`, ` ```splunk-chart`, ` ```splunk-table`).

**Consequences**:
- Adding an agent is just writing a prompt that produces good markdown. Zero UI work.
- Rich rendering (charts, embedded SPL run-buttons, entity links) is a clean future addition — wire a new renderer into the registry without changing the agent contract.
- Sanitization is on by default. Agents cannot inject HTML/JS into the UI.
- A future ADR may add `output_format = json | mixed` to support agents that emit structured data alongside markdown.
