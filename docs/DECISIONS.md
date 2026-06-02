# Splunk Agent Mesh — Architecture Decisions

ADRs are an append-only record. Earlier decisions are preserved even when later
ones supersede them; the `Status` line points to the superseding ADR. For the
narrative of how the architecture evolved, see `docs/legacy/HISTORY.md`.

---

## ADR-001: Backend as FastAPI Service (not Splunk REST Handler)

**Date**: 2026-05-18 · **Status**: Accepted (amended by ADR-014)

A backend is needed for orchestration and LLM calls. Options: a Splunk Custom
REST Handler (runs in-process, awkward dependency management), a standalone
FastAPI service (fast iteration, full async), or frontend-only LLM calls (leaks
API keys — non-starter).

**Chosen**: standalone FastAPI service (`server/agent_mesh/`). Local dev runs
`uvicorn agent_mesh.app:app --port 8765`. ADR-014 later added a Splunk REST
**bridge** in front of it so Splunk Web traffic is authenticated and proxied
rather than hitting uvicorn directly.

---

## ADR-002: Single-Page Tab Navigation (not React Router)

**Date**: 2026-05-18 · **Status**: Accepted

Three views (Investigation / Settings / About). React Router conflicts with
Splunk Web's URL management. **Chosen**: tab navigation via `useState` in the
root `Investigations` component; single webpack bundle. Trade-off: no URL deep
linking; upgradable to multiple Splunk views later.

---

## ADR-003: SettingsStore Abstraction with DevMode Guard

**Date**: 2026-05-18 · **Status**: Superseded in part by ADR-020

API keys must never be plaintext in the repo or browser. **Chosen**: abstract
`SettingsStore` with `SplunkSecureSettingsStore` (Passwords API, production) and
`DevSettingsStore` (reads `AGENT_MESH_API_KEY`; refuses plaintext-to-disk unless
`AGENT_MESH_DEV_MODE=1`). Passwords API activation and sidecar credential-mode
selection were refined by ADR-020.

---

## ADR-004: Deterministic Demo Mode

**Date**: 2026-05-18 · **Status**: Accepted (shape updated by ADR-013)

`demo: true` returns a static result with no LLM/Splunk calls so the demo is
always reliable. ADR-013 changed the demo payload from per-agent markdown to a
canned Threat Hunter **event stream** + one artifact, to mirror the live wire
shape.

---

## ADR-005: React Component Library in Separate Package

**Date**: 2026-05-18 · **Status**: Accepted (inherited)

The scaffold split `@splunk/agent-mesh-ui` (components) and `@splunk/agent-mesh`
(Splunk app). All UI logic lives in the library; the app is a thin entry point.

---

## ADR-006: Agents as Configuration, not Code

**Date**: 2026-05-21 · **Status**: Accepted

The original seven agents were Python classes with hardcoded prompts. To make
the product a platform, agents became `[agent:<id>]` stanzas read from
`agents.conf` (native to Splunk admins, REST-readable, `local/`-overridable).
Adding/tuning an agent is a conf edit, not a code change. This decision still
holds — the agentic refactor changed an agent's *output contract*, not the
config-driven model.

---

## ADR-007: Agents Are Independent in v1

**Date**: 2026-05-21 · **Status**: Superseded by ADR-009, then by ADR-013

v1 kept agents independent (each saw only the user request) to avoid coupling.
Superseded first by cross-agent `depends_on` (ADR-009) and ultimately by the
single-visible-agent model (ADR-013), where one Threat Hunter does the
investigation and delegates only to an internal reporting sub-agent.

---

## ADR-008: Markdown as the Agent Output Lingua Franca

**Date**: 2026-05-21 · **Status**: Superseded by ADR-012 (Threat Hunter)

All agents emitted GitHub-flavored markdown, rendered with `react-markdown` +
sanitization. This was simple and flexible but too loose to drive reliable UI
behavior. Superseded for the Threat Hunter by the structured event contract
(ADR-012). Markdown rendering survives for `final`-summary text and the
reporting sub-agent's internal output.

---

## ADR-009: Cross-Agent Dependencies via `depends_on`

**Date**: 2026-05-24 · **Status**: Superseded by ADR-013; removed in ADR-019

Added an optional `depends_on` DAG so downstream agents could see upstream
findings. Superseded by the single-visible-agent model: the Threat Hunter holds
the full investigation context itself, so cross-agent DAG context is no longer
the mechanism. The `depends_on` field and DAG were deleted entirely in ADR-019.

---

## ADR-010: SSE Streaming for Progressive Rendering

**Date**: 2026-05-24 · **Status**: Accepted (extended by ADR-016, ADR-017)

`/start` launches an async job; `/stream` (SSE) emits progress. Extended later
to stream per-iteration agent updates and per-revision artifact updates
(ADR-016) and to require a signed stream token (ADR-017). Investigation state is
in-memory; a restart loses in-flight runs.

---

## ADR-011: Skills as Post-Processing, Not Tool Use

**Date**: 2026-05-24 · **Status**: Superseded by ADR-012; removed in ADR-019

The `splunk_search` skill was implemented as post-processing: the orchestrator
regex-extracted fenced SPL from completed markdown and executed it. The agent
never saw results. Superseded by the agentic harness loop (ADR-012), where the
agent emits `splunk_search` events, the harness executes one per turn, and feeds
results back. The fenced-SPL post-processing path was deleted in ADR-019.

---

## ADR-012: Agent-Driven Visualization Hints

**Date**: 2026-05-25 · **Status**: Accepted (mechanism moved to event payload)

The agent that writes a search declares its visualization, rather than guessing
from data shape. Originally a fence-tag suffix (` ```spl_column `); now carried
as `payload.type` on a `splunk_search` event (`timechart | table | column |
line | pie | single`, `column` aliases `timechart`). `infer_visualization`
honors the hint first, then falls back to heuristics.

---

## ADR-013: Single Visible Threat Hunter + Reporting Sub-Agent

**Date**: 2026-05-31 · **Status**: Accepted (supersedes ADR-007, ADR-009)

**Context**: Seven peer agents produced loose, hard-to-orchestrate output and a
fragmented UI. The product is really one investigation, narrated by one analyst.

**Chosen**: collapse the mesh to a single user-visible **primary** agent
(`spl_hunter`, "Threat Hunter"). The former `executive_brief` becomes an
internal **subagent** ("Reporting"), invoked only via `handoff` and summarized
back into the Threat Hunter's stream. The other five agents are kept in
`agents.conf` as `enabled = 0`. A new `agent_role` field (`primary | subagent`)
encodes this; the orchestrator runs only primary agents and passes a sub-agent
lookup to the agentic agent.

**Consequences**: a focused, conversational UI centered on one agent; sub-agents
become a reusable internal-delegation pattern; reviving a retired persona is a
one-line conf change.

---

## ADR-014: Delegated Splunk Auth via an Authenticated REST Bridge

**Date**: 2026-05-31 · **Status**: Accepted (amends ADR-001)

**Context**: A single backend admin `SPLUNK_TOKEN` meant every analyst's
searches ran as one identity, and the browser couldn't reach uvicorn cleanly
from Splunk Web.

**Chosen**: a Splunk custom REST endpoint, **`agent_mesh_bridge`**
(`restmap.conf` + `web.conf` + `bin/agent_mesh_bridge.py`), forwards Splunk Web
API calls to uvicorn carrying the analyst's username and session key. The
backend validates the session (`/authentication/current-context`), matches it to
the requesting user, and runs searches as that user (auth scheme `Splunk`). The
service token is a fallback only, gated by
`AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK=1`.

**Consequences**: per-analyst least privilege; no shared admin token on the hot
path; the bridge trusts loopback `X-Splunk-*` headers, so uvicorn must not be
exposed beyond loopback.

---

## ADR-015: Browser-Side Result Fetching (Row Minimization)

**Date**: 2026-05-31 · **Status**: Accepted

**Context**: Returning full Splunk rows through the backend duplicated data and
put search results on a second path.

**Chosen**: the backend returns artifacts **without rows**
(`public_artifact` / `public_investigation`) — only the SID and metadata. The
browser fetches preview and final rows itself from Splunk Web's authenticated
`splunkd/__raw` proxy (`services/splunkSearchResults.ts`). Demo artifacts keep
their rows since they have no real search job.

**Consequences**: rows travel on the analyst's already-authenticated Splunk
path; the backend handles less data; the LLM still receives a truncated row
sample for reasoning during the harness loop.

---

## ADR-016: Harness-Driven Event Loop (not Vendor Tool-Use)

**Date**: 2026-05-31 · **Status**: Accepted (refines the ADR-011 successor)

**Context**: The agentic plan (`docs/AGENTIC_ARCHITECTURE_REVIEW.md`) proposed
Anthropic's native tool-use API. That couples the runtime to one vendor's wire
format.

**Chosen**: the harness drives the loop using plain `LLMProvider.complete()` and
parses a strict JSON event envelope itself (`agents/events.py`). It executes at
most one action per turn (the last `splunk_search` or `handoff`), feeds results
back, and ends on `final`. A finalize turn + synthetic-final guard close out a
budget-exhausted run. Validation tolerates a stray ```` ```json ```` fence and
routes a corrective retry on malformed output.

**Consequences**: provider-agnostic (works for OpenAI/OpenRouter unchanged);
predictable, auditable single-action turns; no blind search chains. The
trade-off is no native parallel tool calls, which the one-action rule wants to
avoid anyway.

---

## ADR-017: Signed, Short-Lived SSE Stream Tokens

**Date**: 2026-05-31 · **Status**: Accepted (extends ADR-010)

**Context**: `EventSource` cannot send auth headers, so the SSE endpoint needed
its own credential.

**Chosen**: `/start` returns a short-lived HMAC-signed `stream_token`
(`stream_tokens.py`, default TTL 4h) bound to the investigation id; `/stream`
validates it. The signing secret is generated per process.

**Consequences**: streams fail closed without a valid token. The per-process
secret means tokens don't survive a restart and multi-worker deployments would
need a shared secret — acceptable for the current single-process POC; seed the
secret from the environment when that changes.

---

## ADR-018: Progressive Search Result Streaming

**Date**: 2026-05-31 · **Status**: Accepted

**Context**: A search card stayed blank until the search finished.

**Chosen**: `SplunkClient` dispatches the job and polls, streaming preview rows
via an `on_update` callback. Each update bumps the artifact's `_revision`; the
job store upserts artifacts by id; the SSE loop re-emits an artifact when its
revision increases. The browser renders pending → running → done.

**Consequences**: live search feedback in the transcript; the SSE de-dup logic
keys on `_revision` rather than first-seen artifact id.

---

## ADR-019: Delete unused single-shot / DAG / fenced-SPL / native-tool-use code

**Date**: 2026-06-01 · **Status**: Accepted (removes the residue of ADR-008,
ADR-009, ADR-011, and the abandoned native-tool-use plan)

**Context**: After committing to the single agentic Threat Hunter (ADR-013) and
the harness event loop (ADR-016), several earlier mechanisms were still in the
tree but unreachable by the shipping mesh — dead alternatives that read as
load-bearing.

**Chosen**: delete them.
- Native tool-use: `AnthropicProvider.complete_with_tools`, `ToolCall`,
  `ToolUseResponse` (the harness uses `complete()` only).
- Single-shot execution: the `LLMAgent` class and the orchestrator's non-agentic
  branch; replaced by a small "no LLM configured" error output.
- The `depends_on` DAG: `_execution_order`, `_dependency_context`, and the
  `depends_on` config field/parsing/descriptor.
- Fenced-SPL post-processing: `extract_spl_blocks` and its regexes plus the
  orphaned viz-hint map in `tools/splunk_search.py` (the `events` module's
  `VIZ_HINT_MAP` is now the single source).
- The five retired SOC stanzas in `agents.conf`.

**Consequences**: the harness/sub-agent (`handoff`) flow is untouched — it runs
via `llm.complete()` + the sub-agent lookup, not any of the above. Reviving a
retired persona now means adding an `agent_mode = agentic` stanza; the old
single-shot/markdown form no longer runs. Net removal of ~340 lines.

---

## ADR-020: Explicit Sidecar Credential Modes

**Date**: 2026-06-02 · **Status**: Accepted (refines ADR-003 and ADR-014)

**Context**: The presence of a service `SPLUNK_TOKEN` silently selected both
Splunk Passwords API storage and REST-backed `agents.conf` reads. A token added
for one purpose could unexpectedly change unrelated behavior. An expired token
also turned Passwords API authentication failures into misleading `502`
responses.

**Chosen**: keep sidecar features independent and opt-in:
- `AGENT_MESH_SETTINGS_STORE=dev|splunk` selects LLM-key storage (`dev` by
  default).
- `AGENT_MESH_CONF_SOURCE=file|splunk` selects the agent-conf source (`file` by
  default).
- `AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK=1` remains the separate opt-in for
  service-token search fallback.

`SPLUNK_TOKEN` is required by the `splunk` modes but its presence alone enables
nothing. Splunk Passwords API `401` and `403` responses remain `401` and `403`
at the sidecar API boundary.

**Consequences**: the POC defaults to env-backed `AGENT_MESH_API_KEY`, repo-file
agent configuration, and delegated analyst search sessions. Startup logs show
the selected modes and whether credentials are configured without printing
secret values.
