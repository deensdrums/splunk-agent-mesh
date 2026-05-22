# Splunk Agent Mesh — Agent Design

Agents are configuration, not code. Each agent is a stanza in `agents.conf`.
This document specifies the stanza format and documents the seven SOC-mesh
agents that ship as the default mesh.

---

## The Agent Stanza

Each `[agent:<id>]` stanza in `agents.conf` becomes one tab in the UI and one
node in the mesh. The runtime ships one generic `LLMAgent` class — all
per-agent behavior lives in the stanza.

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
system_prompt = You are <role>. Given <input description>, respond in <output format>. \
  ...continued on multiple lines via trailing backslash.
```

### Fields

| Field | Required | Type | Default | Notes |
|---|---|---|---|---|
| `system_prompt` | yes | string | — | The LLM system prompt. Multi-line via `\` continuation. |
| `display_name` | no | string | id | Tab label and UI display. |
| `description` | no | string | "" | Shown as a meta line above the tab content. |
| `order` | no | int | 100 | Display and execution order. Lower runs first. Ties broken by id. |
| `enabled` | no | bool | 1 | Disabled agents are excluded entirely. |
| `model` | no | string | (from default) | LLM model identifier. |
| `temperature` | no | float | (from default) | Sampling temperature. |
| `max_tokens` | no | int | 2048 | Cap on completion length. |
| `output_format` | no | string | markdown | Reserved; only `markdown` honored in v1. |
| `skills` | no | csv | "" | Reserved for future skill/tool wiring. |

See `packages/agent-mesh/src/main/resources/splunk/README/agents.conf.spec` for the
canonical reference.

### Input contract

Every agent receives only the original user request as input:

```
description: <user-provided free text>
host: <user-provided, optional>
user: <user-provided, optional>
alert_name: <user-provided, optional>
time_range: <user-provided, optional>
```

Agents do not see each other's outputs in v1. This keeps each agent independent
and makes prompts safer to tune in isolation.

### Output contract

Agents emit GitHub-flavored markdown. The UI renders with `react-markdown` +
`remark-gfm` + `rehype-sanitize`. The `MarkdownView` component supports a
pluggable code-block renderer registry, so future skills can emit ` ```spl`,
` ```splunk-chart`, or ` ```splunk-table` blocks that route to rich components
without touching agent contracts.

---

## Default SOC mesh

The default `agents.conf` ships these seven agents.

### `agent:triage` (order 10)

**Role**: SOC triage analyst.

**Asked to produce**: a Severity classification, an Entities list, and a
Reasoning paragraph. Conservative on Critical.

### `agent:spl_hunter` (order 20)

**Role**: SPL author.

**Asked to produce**: 2-4 candidate SPL searches in fenced ```spl blocks, each
with a short heading explaining what the search finds. Prefers common Splunk
indexes; does not invent custom indexes.

### `agent:timeline` (order 30)

**Role**: Timeline builder.

**Asked to produce**: a markdown table of `Time | Event` rows. Uses relative
times (T+0, T+1m, ...) when exact times aren't available; refuses to fabricate
precise timestamps.

### `agent:blast_radius` (order 40)

**Role**: Lateral-movement / exposure analyst.

**Asked to produce**: a Directly affected list, Recommended pivot searches,
and a Why this matters explanation. Focuses on credential reuse, lateral
movement, and shared infrastructure.

### `agent:detection_gap` (order 50)

**Role**: Detection engineer.

**Asked to produce**: one Splunk detection rule (title, fenced ```spl block,
severity, MITRE techniques, and tuning notes). Behavioral patterns are
preferred over signature matches.

### `agent:response` (order 60)

**Role**: Incident response coordinator.

**Asked to produce**: a numbered list of 3-6 prioritized actions, each with
an `_Approval required: <role>._` line. Opens with a blockquote reminder that
no action runs without approval. Never recommends irreversible destructive
actions without explicit risk notes.

### `agent:executive_brief` (order 70)

**Role**: Executive communicator.

**Asked to produce**: a plain-language summary, Severity, Confidence with
rationale, MITRE techniques, and Recommended next steps pointing the reader to
other agents' tabs. Precise, no overstated certainty.

---

## Adding a new agent

1. Open `packages/agent-mesh/src/main/resources/splunk/default/agents.conf`.
2. Add a new `[agent:<your_id>]` stanza with at minimum `display_name` and
   `system_prompt`.
3. Reload the conf: in Splunk Web, `Settings → Server controls → Restart`,
   or `splunk reload deploy-server`.
4. Refresh the app — a new tab appears.

No backend redeploy. No frontend rebuild. No code changes.
