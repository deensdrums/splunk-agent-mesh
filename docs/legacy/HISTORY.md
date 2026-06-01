# Splunk Agent Mesh — Architecture History

A narrative of how the project reached its current design. This is a curated
history distilled from earlier documentation (the original continuation log, the
pre-refactor architecture/design docs, and the native-tool-use agentic
proposal), kept here so the *current* docs can describe only the present system.
For decisions in record form, see `docs/DECISIONS.md`; for the present design,
`docs/ARCHITECTURE.md`.

---

## 1. Origins — a SOC copilot ("Sentinel Mesh")

The project began as a SOC investigation copilot scaffolded from a Splunk Create
monorepo. The first build (mid-May 2026) shipped a tabbed React app
(Investigation / Settings / About), a FastAPI backend, an LLM provider
abstraction (Anthropic / OpenRouter / OpenAI-compatible), a `SettingsStore`
abstraction with a dev-mode guard, and a deterministic demo. Investigation logic
lived in **seven hardcoded Python agent classes** (triage, spl_hunter, timeline,
blast_radius, detection_gap, response, executive_brief), each with baked-in
prompts, MITRE maps, SPL templates, and severity heuristics.

Early code-review fixes set lasting conventions: backend on port **8765** (to
avoid colliding with Splunk Web on 8000), Pydantic input validation against SPL
injection, and gating the (stubbed) Splunk Passwords store behind a flag.

## 2. The platform pivot — agents as configuration

The project was repositioned from a SOC-specific tool to a **general agentic
platform**, with the SOC mesh as the first example. It was renamed to **Splunk
Agent Mesh** (`sentinel_mesh` → `agent_mesh`, `ai-investigator` →
`agent-mesh`, `investigations` → `agent-mesh-ui`, env vars `SENTINEL_MESH_*` →
`AGENT_MESH_*`).

The seven agent classes were deleted and replaced with **one generic
`LLMAgent`** driven entirely by `[agent:<id>]` stanzas in `agents.conf`, read
via `SplunkRestConfReader` (file fallback for dev). Adding or tuning an agent
became a conf edit, not code. Agent output was **GitHub-flavored markdown**,
rendered with `react-markdown` + sanitization in per-agent tabs. The original
heuristics were archived to `docs/legacy/heuristics.md`. (ADR-006, ADR-008.)

## 3. Cross-agent context and progressive rendering

Two refinements followed. Agents started independent (each saw only the user
request, ADR-007), then gained an optional **`depends_on` DAG** so downstream
agents (timeline, blast_radius, executive_brief) could see upstream findings
(ADR-009). To mask multi-agent latency, the backend added an async job store and
**SSE streaming** so each agent's section appeared as it completed (ADR-010).

The `splunk_search` skill arrived as **post-processing**: an agent emitted
fenced ```` ```spl ```` blocks; the orchestrator regex-extracted and executed
them after the agent finished (ADR-011). Agents controlled chart type via
fence-tag suffixes (` ```spl_column `, ` ```spl_table `, …) which mapped to a
visualization hint, with a data-shape fallback (ADR-012).

## 4. The agentic proposal — and the path not taken

A design review ("Architecture Review: Agentic Loop") diagnosed the core
limitation: every agent was a **single-shot** call followed by blind
post-processing. The model wrote SPL it would never see the results of — it
couldn't observe, iterate, or pivot. The review proposed making `spl_hunter`
agentic using **Anthropic's native tool-use API** (`tools` / `tool_use` /
`tool_result` blocks), adding `agent_mode` and `max_iterations`, and streaming
per-iteration updates.

The agentic loop was built — but the implementation **diverged from the
proposal**. Rather than couple the runtime to one vendor's tool-use wire format,
the loop was made **harness-driven and provider-agnostic**: the model returns
JSON, the harness parses and executes it via plain `complete()`. (That decision
is ADR-016; the original native-tool-use plan is the spirit of this section.)

## 5. The structured-event refactor — one Threat Hunter

The biggest shift collapsed the seven-agent mesh into a **single user-visible
agent**. `spl_hunter` became the "Threat Hunter," the only `primary` agent;
`executive_brief` became an internal "Reporting" **sub-agent** invoked via a
`handoff`; the other five personas were retained in `agents.conf` but disabled.
A new `agent_role` field (`primary | subagent`) encoded the split. (ADR-013.)

Loose markdown gave way to a **strict structured event contract** — a JSON
`{events:[...]}` envelope (`narration | splunk_search | result_summary | finding
| handoff | final`) validated at the LLM boundary (`agents/events.py`), with a
corrective retry (*"Remember to always respond with json."*) and tolerance for a
stray ```` ```json ```` fence. The harness executes **one action per turn**
(the last `splunk_search` or `handoff`), feeds results back, and ends on
`final`, with a finalize-turn + synthetic-final guard so a budget-exhausted run
never dangles. (ADR-012, ADR-016.)

## 6. Auth and streaming overhaul

Live access moved off a shared admin token to the **analyst's delegated Splunk
session**, forwarded through a Splunk-authenticated `agent_mesh_bridge` REST
endpoint and validated per request; the service `SPLUNK_TOKEN` became a gated
fallback (ADR-014). Search **rows were removed from the API**, with the browser
fetching them directly from Splunk Web's authenticated proxy (ADR-015). The SSE
stream gained **signed, short-lived stream tokens** (ADR-017), and searches
began **streaming preview rows** into the cards via artifact revisions (ADR-018).

## 7. UI evolution

The report UI moved through three stages: per-agent **tabs** → stacked **report
sections** per agent → a single **console workspace** for the Threat Hunter.
The console added staggered one-at-a-time event reveal, stick-to-bottom
auto-follow, a persistent status bar (investigation/agent state, event count,
id), inline live charts, and an animated "thinking" indicator — and dropped the
outer card and the separate "Agent Work Details" panel in favor of an open,
bounded transcript.

---

## Where the old model still lingers

Some pre-refactor machinery remains in the codebase, intentionally:

- The generic single-shot `LLMAgent`, the `depends_on` DAG, and the fenced-SPL
  post-processing path still exist — used by `single_shot` agents, though none
  ship enabled today.
- The five specialized SOC personas remain as `enabled = 0` stanzas, revivable
  in one line.
- `docs/legacy/heuristics.md` preserves the original pre-platform heuristics.
- A handful of `components/legacy/` React components from the first SOC UI are
  retained but unused (slated for removal).
