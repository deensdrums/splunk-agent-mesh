# Splunk Agent Mesh — Agent Design

Agents are configuration, not code. Each agent is a stanza in `agents.conf`.
This document specifies the stanza format and documents the seven SOC-mesh
agents that ship as the default mesh.

---

## The Agent Stanza

Each `[agent:<id>]` stanza in `agents.conf` becomes one section in the
investigation report and one node in the orchestrator's execution DAG. The
runtime ships one generic `LLMAgent` class — all per-agent behavior lives in
the stanza.

```ini
[default]
enabled = 1
model = claude-sonnet-4-6
temperature = 0.2
max_tokens = 2048
output_format = markdown

[agent:my_agent]
display_name = My Agent
description = One-line description shown in the UI.
order = 100
skills = splunk_search
depends_on = triage
system_prompt = You are <role>. Given <input description>, respond in <output format>. \
  ...continued on multiple lines via trailing backslash.
```

### Fields

| Field | Required | Type | Default | Notes |
|---|---|---|---|---|
| `system_prompt` | yes | string | — | The LLM system prompt. Multi-line via `\` continuation. |
| `display_name` | no | string | id | Section heading in the report. |
| `description` | no | string | "" | Shown in agent listings. |
| `order` | no | int | 100 | Execution order. Lower runs first. Ties broken by id. |
| `enabled` | no | bool | 1 | Disabled agents are excluded entirely. |
| `model` | no | string | (from default) | LLM model identifier. |
| `temperature` | no | float | (from default) | Sampling temperature. |
| `max_tokens` | no | int | 2048 | Cap on completion length. |
| `output_format` | no | string | markdown | Reserved; only `markdown` honored currently. |
| `skills` | no | csv | "" | Named skills the agent may invoke. Currently supported: `splunk_search`. |
| `depends_on` | no | csv | "" | Agent ids that must complete before this agent runs. Dependent agents receive prior outputs as context. |

See `packages/agent-mesh/src/main/resources/splunk/README/agents.conf.spec` for the
canonical reference.

### Input contract

Every agent receives the original user request:

```
description: <user-provided free text>
host: <user-provided, optional>
user: <user-provided, optional>
alert_name: <user-provided, optional>
time_range: <user-provided, optional>
```

Agents with `depends_on` also receive a `dependency_context` block containing
the markdown output and artifact metadata from their upstream agents.

### Output contract

Agents emit GitHub-flavored markdown. The UI renders with `react-markdown` +
`remark-gfm` + `rehype-sanitize`.

Agents with `skills = splunk_search` should emit fenced SPL blocks using
visualization-hinted fence tags:

| Fence tag | Visualization | Use when |
|---|---|---|
| ` ```spl_column ` | Column chart | `timechart count` or time-bucketed aggregations |
| ` ```spl_line ` | Line chart | Time-series trends |
| ` ```spl_bar ` | Bar chart | `stats count by ...` categorical comparisons |
| ` ```spl_pie ` | Pie chart | Proportional breakdowns |
| ` ```spl_single ` | Single value | One numeric metric |
| ` ```spl_table ` | Data table | Tabular listings, detection rules |
| ` ```spl ` | Auto-inferred | Fallback (heuristic picks based on data shape) |

The orchestrator extracts these blocks post-completion, executes them against
Splunk, and attaches the results as structured artifacts rendered inline in the
report.

---

## Default SOC mesh

The default `agents.conf` ships these seven agents.

### `agent:triage` (order 10)

**Role**: SOC triage analyst.
**Skills**: none
**Dependencies**: none

**Asked to produce**: a Severity classification, an Entities list, and a
Reasoning paragraph. Conservative on Critical.

### `agent:spl_hunter` (order 20)

**Role**: SPL author.
**Skills**: `splunk_search`
**Dependencies**: none

**Asked to produce**: 2-4 candidate SPL searches in visualization-hinted fenced
blocks, each with a short heading explaining what the search finds. Uses
`spl_column` for timecharts, `spl_table` for listings, etc. Prefers common
Splunk indexes; does not invent custom indexes.

### `agent:timeline` (order 30)

**Role**: Timeline builder.
**Skills**: none
**Dependencies**: `spl_hunter`

**Asked to produce**: a markdown table of `Time | Event` rows. Uses relative
times (T+0, T+1m, ...) when exact times aren't available; refuses to fabricate
precise timestamps.

### `agent:blast_radius` (order 40)

**Role**: Lateral-movement / exposure analyst.
**Skills**: none
**Dependencies**: `triage`, `spl_hunter`

**Asked to produce**: a Directly affected list, Recommended pivot searches,
and a Why this matters explanation. Focuses on credential reuse, lateral
movement, and shared infrastructure.

### `agent:detection_gap` (order 50)

**Role**: Detection engineer.
**Skills**: `splunk_search`
**Dependencies**: none

**Asked to produce**: one Splunk detection rule (title, fenced `spl_table` block,
severity, MITRE techniques, and tuning notes). Behavioral patterns are
preferred over signature matches.

### `agent:response` (order 60)

**Role**: Incident response coordinator.
**Skills**: none
**Dependencies**: `triage`, `blast_radius`

**Asked to produce**: a numbered list of 3-6 prioritized actions, each with
an `_Approval required: <role>._` line. Opens with a blockquote reminder that
no action runs without approval. Never recommends irreversible destructive
actions without explicit risk notes.

### `agent:executive_brief` (order 70)

**Role**: Executive communicator.
**Skills**: none
**Dependencies**: `triage`, `timeline`, `blast_radius`, `detection_gap`, `response`

**Asked to produce**: a plain-language summary, Severity, Confidence with
rationale, MITRE techniques, and Recommended next steps. Precise, no overstated
certainty.

---

## Adding a new agent

1. Open `packages/agent-mesh/src/main/resources/splunk/default/agents.conf`.
2. Add a new `[agent:<your_id>]` stanza with at minimum `display_name` and
   `system_prompt`.
3. Optionally add `skills = splunk_search` if the agent should run SPL queries.
4. Optionally add `depends_on = <agent_id>` if it needs prior agent context.
5. Reload the conf: in Splunk Web, `Settings → Server controls → Restart`,
   or `splunk reload deploy-server`.
6. Refresh the app — a new section appears in the investigation report.

No backend redeploy. No frontend rebuild. No code changes.
