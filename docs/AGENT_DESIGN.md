# Splunk Agent Mesh — Agent Design

Agents are configuration, not code. Each agent is an `[agent:<id>]` stanza in
`agents.conf`. This document specifies the stanza format, the Threat Hunter's
**structured event contract**, and the agents that ship today.

---

## The agent stanza

```ini
[default]
enabled = 1
model = claude-sonnet-4-6
temperature = 0.2
max_tokens = 2048
output_format = markdown

[agent:spl_hunter]
display_name = Threat Hunter
description = Investigates incidents by iteratively searching Splunk and reports findings.
agent_mode = agentic
agent_role = primary
skills = splunk_search
max_iterations = 14
max_tokens = 4096
system_prompt = You are the Threat Hunter ... respond with VALID JSON ONLY ...
```

### Fields

| Field | Required | Type | Default | Notes |
|---|---|---|---|---|
| `system_prompt` | yes | string | — | LLM system prompt. Multi-line via trailing `\`. |
| `display_name` | no | string | id | Name shown in the report. |
| `description` | no | string | "" | Shown in agent listings. |
| `order` | no | int | 100 | Execution order (lower first; ties by id). |
| `enabled` | no | bool | 1 | Disabled stanzas are excluded entirely. |
| `agent_mode` | no | string | single_shot | `agentic` (harness event loop) or `single_shot`. |
| `agent_role` | no | string | primary | `primary` (user-visible) or `subagent` (delegated). |
| `max_iterations` | no | int | 10 | Safety cap on agentic loop turns. |
| `model` | no | string | (default) | LLM model identifier. |
| `temperature` | no | float | (default) | Sampling temperature. |
| `max_tokens` | no | int | 2048 | Completion length cap. |
| `skills` | no | csv | "" | Named skills. Currently supported: `splunk_search`. |
| `depends_on` | no | csv | "" | Single-shot DAG edges; ignored by agentic agents. |

See `packages/agent-mesh/src/main/resources/splunk/README/agents.conf.spec` for
the canonical Splunk spec.

### Input contract

Every agent receives the original user request:

```
description: <free text>
host:        <optional>
user:        <optional>
alert_name:  <optional>
time_range:  <optional>
```

---

## The Threat Hunter response contract

A `primary` agent with `agent_mode = agentic` (the Threat Hunter) **must
respond with valid JSON only** — no markdown, no prose, no code fences. The
top-level value is an object with a non-empty `events` array; each event is:

```json
{ "type": "...", "title": "string", "text": "string", "payload": { } }
```

`type` is one of `narration`, `splunk_search`, `result_summary`, `finding`,
`handoff`, `final`. `payload` is always an object (`{}` when empty).

| Type | When to use | Payload |
|---|---|---|
| `narration` | Explain the current step at a high level | `{}` |
| `splunk_search` | Propose/execute one SPL query | `query` (SPL), `purpose`, `type` (viz hint) |
| `result_summary` | Summarize search or sub-agent results | `{}` |
| `finding` | A security-relevant observation | structured fields, e.g. `user`, `src_ip`, `confidence` |
| `handoff` | Delegate to a sub-agent | `{ "sub_agent": "executive_brief", "task": "summarize_findings" }` |
| `final` | The closing answer | `summary`, `recommended_actions` (array) |

### Example response

```json
{
  "events": [
    { "type": "narration", "title": "Starting investigation",
      "text": "I'll confirm the encoded PowerShell, then bound the blast radius.",
      "payload": {} },
    { "type": "splunk_search", "title": "Encoded PowerShell on the host",
      "text": "Looking for powershell.exe launched with an encoded command.",
      "payload": {
        "query": "index=endpoint host=FIN-LAPTOP-22 process_name=powershell.exe (\"-enc\" OR \"-EncodedCommand\") | timechart span=1m count",
        "purpose": "Confirm execution and timing",
        "type": "timechart"
      } }
  ]
}
```

### Loop behavior (harness rules)

- Emit **at most one action event** (`splunk_search` or `handoff`) per response,
  and make it the **last** event.
- To run a search: end with a `splunk_search` event. The harness executes it,
  appends the results, and calls the agent again to interpret them.
- To produce a report: end with a `handoff` event (`sub_agent =
  executive_brief`). The harness runs the reporting sub-agent and returns its
  output; the agent then emits a `result_summary` and a `final`.
- Finish with a `final` event and request no further action.
- On `"Remember to always respond with json."`, resend as valid JSON.

### Visualization hints

`splunk_search` `payload.type` controls the inline chart:
`timechart | table | column | line | pie | single` (`column` aliases
`timechart`). `ArtifactRenderer` renders Column/Line/Pie via
`@splunk/visualizations`, and a native table for tabular data.

---

## The shipping mesh

### `agent:spl_hunter` — "Threat Hunter" (primary, agentic)

**Role**: the investigator and the only user-visible agent.
**Skills**: `splunk_search`. **Mode**: `agentic`, `max_iterations = 14`.

Runs the think → search → observe → report loop and emits the structured event
stream above. Prompted to use common Splunk indexes (`main`, `endpoint`, `dns`,
`auth`, `proxy`, `firewall`, `web`, `os`, `sysmon`) and real CIM field names,
and to broaden or pivot when a search returns nothing.

### `agent:executive_brief` — "Reporting" (subagent)

**Role**: turns the investigation's findings into a concise leadership report
(executive summary, severity, confidence, MITRE ATT&CK, next steps).

Invoked **only** via a Threat Hunter `handoff`. Its markdown output is fed back
to the Threat Hunter, which summarizes it through `result_summary` + `final`. It
never appears in the UI as a peer agent.

### Disabled agents (retained, `enabled = 0`)

`triage`, `timeline`, `blast_radius`, `detection_gap`, `response` — the original
SOC personas. They are kept in `agents.conf` for easy revival but are not run.
The Threat Hunter now narrates triage, timeline, blast-radius, detection, and
response inline as part of its event stream. See `docs/legacy/HISTORY.md` for
why the 7-agent mesh collapsed to one visible agent.

---

## Adding or changing an agent

1. Edit `packages/agent-mesh/src/main/resources/splunk/default/agents.conf`.
2. To add a user-visible agentic agent, set `agent_mode = agentic`,
   `agent_role = primary`, `skills = splunk_search`, and a system prompt that
   enforces the event contract above.
3. To add a delegated capability, set `agent_role = subagent` and reference it
   from a primary agent's `handoff` payload (`sub_agent = <id>`).
4. Reload conf (Splunk Web: **Settings → Server controls → Restart**, or
   `splunk reload deploy-server`).

No backend redeploy, no frontend rebuild for prompt/stanza changes. Changing the
event contract itself requires updating `agents/events.py` and the renderers.
