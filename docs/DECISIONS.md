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
- Local dev requires running `uvicorn agent_mesh.app:app` separately.
- The Splunk app React code calls `http://localhost:8000` (configurable) in dev, and will call the Splunk REST proxy in production.
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

**Context**: The Splunk Create scaffold created two packages: `investigations` (component library) and `splunk-agent-mesh` (Splunk app). All React UI logic lives in `investigations`. The Splunk app imports from it.

**Consequences**:
- UI changes go in `packages/investigations/src/`.
- Splunk app pages (`packages/splunk-agent-mesh/src/main/webapp/pages/`) are thin entry points only.
- This is a clean separation that allows the component library to be tested standalone (via `start:demo`).
