# The Agentic Loop — As Built

> This document originally proposed making `spl_hunter` agentic via Anthropic's
> native tool-use API. The implementation took a different path — a
> **harness-driven JSON event loop** that is provider-agnostic — and the Threat
> Hunter became the single user-visible agent. This document now describes what
> was actually built. The original proposal is preserved in
> `docs/legacy/HISTORY.md`; the decision to diverge is ADR-016.

---

## Summary

The Threat Hunter (`spl_hunter`) runs a think → search → observe → report loop.
The model never executes anything itself: it returns a structured JSON event
stream, and the **harness** (`agents/agentic_llm_agent.py`) decides what to run.
This keeps the runtime provider-agnostic, the turns auditable, and the UI fed
with validated events only.

## Why not native tool-use

Native tool-use (Anthropic `tools` / `tool_use` blocks) would couple the runtime
to one vendor's wire format and complicate the `LLMProvider` interface. Instead
the loop uses plain `complete()` and parses a strict event envelope. The same
loop works unchanged for OpenAI/OpenRouter. Trade-off: no provider-native
parallel tool calls — but the design deliberately runs **one action per turn**
anyway, so nothing is lost.

## The loop

```
messages = [system_prompt, user_request]
for iteration in range(max_iterations):
    response = llm.complete(messages)
    events, corrective = parse_and_validate(response)   # agents/events.py
    if corrective:                                       # malformed output
        append assistant(response) + user(corrective)    # "Remember to always respond with json."
        continue
    record events; stream them to the UI
    action = last event if its type in {splunk_search, handoff} else None
    if action == splunk_search:
        run SPL → artifact; append truncated rows to messages; loop
    elif action == handoff:
        run sub-agent; append its output to messages; loop
    else:
        stop                                             # final / informational terminal
# budget exhausted mid-action → one finalize turn, then a synthetic final
```

### Rules and guarantees

- **One external action per turn**, taken from the *last* event. No blind chains
  of dependent searches.
- **Validation at the boundary**: `parse_and_validate` enforces the schema,
  tolerates a single ```` ```json ```` fence, and routes a corrective retry on
  failure. Only validated events ever reach the UI.
- **Sub-agent calls** are harness-managed request/response LLM calls. Handoff
  still feeds a named subagent's markdown back to the Threat Hunter, while
  lifecycle policies can invoke the search optimizer before search execution
  and reporting/labeling subagents after final.
- **Termination guarantee**: if `max_iterations` is hit with an action pending,
  the harness makes one finalize call; if that yields no terminal event, it
  appends a harness-authored `final` so the transcript never dangles.

## Tools the agent has today

| Tool | Mechanism | Input | Output to LLM |
|---|---|---|---|
| `splunk_search` | `splunk_search` event → optional `search_optimizer` → `run_splunk_search_artifact` | `query`, `purpose`, `type` (viz hint) | status, requested/executed query, optimization metadata, fields, **truncated** rows (≤20), `row_count`, `sid` |
| `handoff` | `handoff` event → sub-agent `complete()` | `sub_agent`, `task` | the sub-agent's report text |
| `after_final` subagents | `invoke_policy = after_final` → sub-agent `complete()` | completed request, events, artifact summaries | harness-authored `result_summary` / `finding` events inserted before `final` |

Full rows are stored in the artifact for the UI (fetched by the browser from
Splunk Web), not sent to the LLM — the model reasons over a truncated sample.

## Streaming

A per-iteration progress callback emits the agent's accumulated events plus any
newly-revised artifacts. `SplunkClient` streams search preview rows via an
`on_update` callback; each update bumps the artifact `_revision`, and the SSE
loop re-emits artifacts whose revision changed. The browser renders pending →
running → done with live charts.

## State and context

The `messages` list is the working memory: system prompt, user request,
assistant event-JSON per turn, and appended search/handoff results. Mitigations
against context bloat: truncate search rows to ~20 + counts, cap turns with
`max_iterations` (14 for the Threat Hunter), and the finalize turn to close out.

## Safety / governance

- **Read-only**: the agent can search Splunk but cannot modify data or take
  response actions; recommended actions are surfaced for human approval.
- **Least privilege**: searches run as the analyst's delegated Splunk session
  (ADR-014), inheriting that user's access and the investigation time range.
- **Cancellable**: the existing cancel endpoint stops a running investigation.
- **Cost**: `max_iterations` is the primary cap; each turn is one LLM call.

## Possible next steps

- **Discovery tools** (index / sourcetype / field summaries) so the agent
  explores the environment instead of guessing field names.
- **Optimizer evaluation** to measure whether before-search rewrites improve
  search cost/latency without changing analyst conclusions.
- **Token-level streaming** within a turn (provider streaming API) for
  character-by-character rendering — independent of this loop.
