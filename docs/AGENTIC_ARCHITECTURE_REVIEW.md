# Architecture Review: Agentic Loop for Splunk Agent Mesh

## Executive Summary

The current system runs each persona as a **single-shot LLM call** followed by **post-hoc tool execution**. The model generates markdown blindly, the harness regex-extracts SPL blocks and runs them, and the model never sees the results. This is fundamentally non-agentic: the agent cannot observe, reason about, or react to evidence.

Moving `spl_hunter` (and potentially other personas) to an agentic loop is architecturally feasible without replacing the persona/conf system. The key change is replacing `LLMAgent.run()` — currently a single `llm.complete()` call — with an iterative loop that uses the Anthropic tool-use API. The `agents.conf` system, `depends_on` DAG, SSE streaming, and artifact infrastructure all survive intact. The main cost is provider coupling: the tool-use API shape differs between Anthropic, OpenAI, and OpenRouter, so the `LLMProvider` abstraction needs a second method or a new subclass.

The recommended path is a phased approach: first, make `spl_hunter` agentic with `splunk_search` as a native tool (not post-processing). Then extend the SSE stream to emit per-iteration updates. Then evaluate which other personas benefit from agentic behavior. Most will not.

---

## 1. Current-State Assessment

### How the persona system works

```
agents.conf stanza
      |
      v
  AgentConfig (id, system_prompt, model, skills, depends_on)
      |
      v
  LLMAgent.run(request)
      |
      +-- Build messages: [system_prompt, user_request + dependency_context]
      +-- Single call: llm.complete(messages) -> CompletionResponse
      +-- Return: {status, markdown, model, timestamps}
      |
      v
  Orchestrator._run_agent_tools(cfg, request, output)
      |
      +-- If "splunk_search" in cfg.skills:
      |     +-- Regex-extract spl blocks from markdown
      |     +-- Execute each against Splunk (max 4)
      |     +-- Return artifact dicts with rows/fields/viz
      +-- Else: return []
```

### Where `spl_hunter` is non-agentic

`spl_hunter` (`llm_agent.py:56`) makes exactly one LLM call. The model proposes 2-4 SPL searches based purely on the investigation description. It has:

- **No observation**: The model never sees search results. It writes SPL and the harness runs it after the model is done.
- **No iteration**: If a search returns 0 results, or if the data reveals a new lead, the model cannot pivot.
- **No planning**: There's no think-search-observe-decide loop. The model produces its entire output in one pass.
- **No validation**: The model cannot verify that a proposed search actually returns evidence. It guesses at index names, field names, and sourcetypes.
- **No tool invocation**: The Anthropic SDK supports native tool use (`tools` parameter, `tool_use`/`tool_result` content blocks). The current `LLMProvider.complete()` interface doesn't expose this — it returns `CompletionResponse.content: str`, discarding any tool-use blocks.

### What's missing

| Capability | Status | Gap |
|---|---|---|
| Tool-use API | Anthropic SDK 0.104.1 supports it | `LLMProvider.complete()` returns `str`, not structured content blocks |
| Multi-turn conversation | Not supported | `LLMAgent.run()` sends one user message, gets one response |
| Iteration control | Not supported | No loop, no stopping criteria, no max-iterations guard |
| Per-iteration streaming | Not supported | SSE emits once per agent completion, not per loop iteration |
| Tool result injection | Not supported | No mechanism to feed search results back into the conversation |
| Scratchpad / working memory | Not supported | No accumulation of intermediate findings across turns |

---

## 2. Compatibility with the Config System

### What survives unchanged

- **`agents.conf` stanzas**: The persona concept is purely configuration. An agentic `spl_hunter` is still an `[agent:spl_hunter]` stanza with a system prompt, model, and skills. The stanza just gains new semantics.
- **`depends_on` DAG**: Downstream agents (timeline, blast_radius, executive_brief) still wait for `spl_hunter` to fully complete before they run. The DAG doesn't care whether `spl_hunter` took 1 turn or 10.
- **`skills` field**: Already parsed and honored. Currently used for post-processing dispatch. In the agentic model, `skills = splunk_search` would instead mean "this agent gets `splunk_search` as a native tool in its tool-use API call."
- **Artifact infrastructure**: `run_splunk_search_artifact()` already produces properly shaped artifacts. The agentic loop would call the same function — just from inside the loop rather than after it.

### What needs extension

- **New stanza field: `agent_mode`** — Distinguishes single-shot agents from agentic ones. Values: `single_shot` (default, current behavior) or `agentic`. This lets non-investigative personas (triage, timeline, response, executive_brief) remain simple while `spl_hunter` and `detection_gap` get the loop.
- **New stanza field: `max_iterations`** — Safety cap for the agentic loop. Default: 10. Prevents runaway tool-use cycles.
- **New stanza field: `tool_timeout`** — Per-tool execution timeout. Default: 30s.
- **System prompt changes** — Agentic agents need prompts that instruct the model to think, search, observe, and synthesize rather than produce final output in one shot.

---

## 3. Agentic Loop Requirements

### Loop structure

```
+--------------------------------------------------+
|  Initialize: system_prompt + user request        |
|  messages = [system, user]                       |
+---------------------+----------------------------+
                      |
             +--------v--------+
             |  LLM call with  |
             |  tools defined  |<-----------------+
             +--------+--------+                  |
                      |                           |
             +--------v--------+                  |
             |  Response has   |  yes             |
             |  tool_use?      +--------+         |
             +--------+--------+        |         |
                      | no              |         |
             +--------v--------+  +-----v------+  |
             |  Return final   |  |  Execute   |  |
             |  markdown       |  |  tool      |  |
             +-----------------+  +-----+------+  |
                                        |         |
                                  +-----v------+  |
                                  | Append     |  |
                                  | tool_result+--+
                                  | to messages|
                                  +------------+
```

### Stopping criteria

The loop ends when:
1. The model returns a response with no `tool_use` blocks (it's done investigating)
2. `max_iterations` is reached (safety cap)
3. The investigation is cancelled by the user
4. A fatal error occurs (LLM provider down, Splunk unreachable)

### Which personas should become agentic

| Persona | Recommendation | Rationale |
|---|---|---|
| `triage` | **Stay single-shot** | Classification from description alone. No tool use needed. |
| `spl_hunter` | **Agentic** | Core investigator. Must search, observe results, pivot, validate. |
| `timeline` | **Stay single-shot** | Synthesizes upstream context into a table. No tools. |
| `blast_radius` | **Stay single-shot** | Analysis of upstream findings. Could become agentic later if it gains search capability. |
| `detection_gap` | **Potentially agentic** | Could validate that proposed detection rules actually match data. Lower priority than `spl_hunter`. |
| `response` | **Stay single-shot** | Recommends actions. No tool use. |
| `executive_brief` | **Stay single-shot** | Synthesizes everything. No tools. |

---

## 4. System Design Options

### Option A: Agentic LLMAgent subclass (Recommended)

Create `AgenticLLMAgent` alongside the existing `LLMAgent`. The orchestrator checks `cfg.agent_mode` and instantiates the right class. `LLMAgent` stays untouched — zero risk to the 5 single-shot personas.

```python
class AgenticLLMAgent:
    def run(self, request, tools, progress_callback) -> dict:
        messages = [system, user]
        for iteration in range(max_iterations):
            response = llm.complete_with_tools(messages, tools)
            # emit progress: markdown so far + any new artifacts
            if response.stop_reason != "tool_use":
                break
            for tool_call in response.tool_calls:
                result = execute_tool(tool_call)
                messages.append(tool_call_message)
                messages.append(tool_result_message)
        return final_output
```

**Pros**: Clean separation. Single-shot agents untouched. Easy to test independently.
**Cons**: Some code duplication between `LLMAgent` and `AgenticLLMAgent` (error handling, output formatting).

### Option B: Unified LLMAgent with optional loop

Modify `LLMAgent.run()` to support an optional tool-use loop. If `cfg.skills` is empty or `cfg.agent_mode == "single_shot"`, it behaves exactly as today. If `agent_mode == "agentic"`, it enters the loop.

**Pros**: One agent class. Shared error handling.
**Cons**: Increases complexity of `LLMAgent`. Risk of regressions in single-shot personas.

### Option C: Orchestrator-driven loop

The orchestrator itself runs the loop: call agent, extract tool calls, execute tools, re-call agent. The agent class stays a single-call wrapper.

**Pros**: Agent class stays dead simple. Orchestrator has full control.
**Cons**: Orchestrator becomes complex. Tool execution and conversation management entangle with scheduling logic.

### Recommendation: Option A

Option A gives the clearest separation. The existing 5 single-shot agents continue to work exactly as they do today. The agentic behavior is fully contained in a new class with its own test surface. The orchestrator adds one `if` branch to pick the right class.

---

## 5. Tooling and Execution Model

### Tools `spl_hunter` needs

**Must-have (Phase 1):**

| Tool | Input | Output |
|---|---|---|
| `splunk_search` | `{spl, earliest, latest, viz_hint}` | `{status, fields, rows, sid, error, row_count}` |

**Nice-to-have (Phase 2+):**

| Tool | Input | Output |
|---|---|---|
| `get_field_summary` | `{index, sourcetype, field}` | `{distinct_values, top_10, count}` |
| `list_sourcetypes` | `{index}` | `{sourcetypes: [...]}` |
| `get_indexes` | `{}` | `{indexes: [...]}` |

The discovery tools (field summary, sourcetype list, index list) let the agent explore the environment instead of guessing at field names and sourcetypes — a major accuracy improvement.

### LLMProvider changes

The `LLMProvider.complete()` interface returns `CompletionResponse(content: str)`. Tool use requires returning structured content blocks. Two approaches:

**Approach 1: New method (Recommended)** — Add `complete_with_tools(messages, tools, ...) -> ToolUseResponse` to `LLMProvider`. Only providers that support tool use implement it. The base class raises `NotImplementedError`. This preserves backward compatibility.

**Approach 2: Extend complete()** — Change `CompletionResponse` to carry optional tool-use blocks. Less clean but fewer methods.

Recommendation: Approach 1. The Anthropic SDK already has distinct request shapes for tool-use vs. plain completion. Trying to unify them adds complexity.

### Visualization hints

The agent that generates a search provides the visualization hint as part of the tool call input (e.g., `viz_hint: "column"`), instructed via the system prompt. This is consistent with the current fence-tag approach and has produced strong results in practice.

Future improvement: a sub-agent search optimizer that double-checks searches one-at-a-time (invoked as a tool call by the agentic agent). This optimizer could refine both the SPL and the viz hint before execution. For now, relying on the generating agent's system prompt is sufficient.

### Tool result truncation

Splunk searches can return large result sets. The agent doesn't need 100 rows to reason — it needs a summary. Tool results should be truncated before injection:
- Max 20 rows in the tool result message to the LLM
- Full results still stored in the artifact for the UI
- Include a `total_rows` count so the agent knows if results were truncated

### Failure handling

- **Search returns 0 rows**: The agent sees this and can reformulate. This is the core value of the agentic loop.
- **Search errors**: The tool returns an error message. The agent can retry with modified SPL or move on.
- **Search timeout**: 30-second timeout per search. The agentic `spl_hunter` is expected to run needle-in-the-haystack queries that need more time than the current 8-second default. Future work can add more complex harness logic for long-running searches using search hints and a search-optimizing LLM.
- **LLM error mid-loop**: Return whatever markdown the agent has produced so far, plus artifacts from completed iterations. Partial results are better than no results.

### Auditability

Every tool call and result should be logged in the investigation's `audit` trail:
```python
audit_event("tool_call", investigation_id, username,
            agent_id=cfg.id, tool="splunk_search",
            iteration=n, spl=spl)
audit_event("tool_result", investigation_id, username,
            agent_id=cfg.id, tool="splunk_search",
            iteration=n, row_count=len(rows), status=status)
```

---

## 6. State, Memory, and Context Management

### What persists across iterations

The conversation `messages` list is the primary state. It accumulates:
- System prompt (fixed)
- User request (fixed)
- Assistant responses (growing — one per iteration)
- Tool calls and results (growing — one pair per tool invocation)

### Context bloat risk

With a 200k context window (Claude Sonnet), the risk is manageable for a typical investigation (5-10 iterations, each with a few hundred tokens of tool results). But uncapped search results would blow it up.

**Mitigations:**
- Truncate tool results to 20 rows + summary stats
- Set `max_iterations` (default 10, configurable per stanza)
- If context approaches a threshold (e.g., 80% of max), inject a summarization instruction and let the agent synthesize what it has

### Intermediate findings representation

The agent produces cumulative markdown across iterations. Each iteration may yield:
- A reasoning paragraph ("Based on the 47 process events, I see...")
- A new search to run
- Updated conclusions

The UI renders the agent's section cumulatively — it updates on every iteration with the latest markdown. The final state is whatever the agent has produced when it stops calling tools. The system prompt should instruct the agent to maintain a coherent, cumulative document rather than emitting disconnected fragments.

### Downstream agent context

Downstream agents (those with `depends_on = spl_hunter`) receive only the final output — not intermediate iterations. This keeps downstream prompts clean and avoids injecting the agent's exploratory reasoning into contexts where it would be noise.

---

## 7. Safety, Reliability, and Governance

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Runaway loop (agent never stops calling tools) | High | `max_iterations` cap (stanza-configurable, hard default 10) |
| Excessive Splunk load | Medium | Max 4 searches per iteration, rate limiting on SplunkClient |
| Context window exhaustion | Low | Result truncation, iteration cap |
| Hallucinated SPL causes Splunk errors | Low | Already handled — `SplunkClient` returns error, agent sees it |
| Agent fabricates evidence from search results | Medium | Audit trail logs every tool call/result. UI shows raw artifacts alongside agent prose so analysts can verify. |
| Cost (many LLM calls per investigation) | Medium | `max_iterations` cap. Future: per-investigation cost budget configurable in conf. |

### Guardrails

- **Read-only tools only**: The agent can search Splunk but cannot modify data, create alerts, or take response actions.
- **Search scope**: All searches inherit the investigation's time range. The agent cannot query `-10y`.
- **Iteration visibility**: Each iteration's tool calls and results are visible in the audit trail and (with the streaming change) in the UI.
- **Human-in-the-loop**: The user can cancel a running investigation at any time via the existing cancel endpoint.

---

## 8. Phased Implementation Plan

### Phase 1: Minimal Agentic `spl_hunter`

**Goal**: `spl_hunter` runs a think-search-observe loop. Each iteration is visible in the UI via cumulative markdown updates and progressive artifact rendering.

**Changes:**
1. Add `complete_with_tools()` to `AnthropicProvider` (the only provider in active use).
2. Create `AgenticLLMAgent` with the iteration loop.
3. Add `agent_mode` and `max_iterations` to `AgentConfig` and `agents.conf.spec`.
4. Orchestrator instantiates `AgenticLLMAgent` when `agent_mode == "agentic"`.
5. Progress callback fires per iteration (not just on agent completion).
6. SSE stream emits `agent_iteration` events so the UI can show the agent's progress mid-loop.
7. Update `spl_hunter` stanza: `agent_mode = agentic`, rewrite system prompt for iterative investigation.
8. Increase tool timeout to 30 seconds for agentic search execution.

**Validation**: Run against real Splunk data. Compare investigation quality (evidence found, search relevance) between single-shot and agentic `spl_hunter`.

**Risk**: Moderate. Constrained to one persona. Fallback: set `agent_mode = single_shot` to revert.

### Phase 2: Per-iteration UI streaming

**Goal**: The user sees each iteration live — the agent's reasoning, the search it runs, the results appearing as charts.

**Changes:**
1. New SSE event type: `agent_iteration` with `{agent_id, iteration, markdown_delta, artifacts}`.
2. Frontend accumulates markdown deltas and artifacts per iteration.
3. Consider token-level streaming within each iteration (Anthropic streaming API).

### Phase 3: Search optimizer sub-agent

**Goal**: A tool-callable sub-agent that double-checks individual searches before execution — validating SPL syntax, refining field names, and confirming viz hints.

**Changes:**
1. New tool: `optimize_search` — takes a proposed SPL query, runs validation logic and/or a lightweight LLM call, returns refined SPL + viz hint.
2. The agentic `spl_hunter` calls this tool before executing expensive searches.
3. Configurable per-stanza whether search optimization is enabled.

### Phase 4: Discovery tools and `detection_gap`

**Goal**: Add index/sourcetype/field discovery tools. Make `detection_gap` agentic so it can validate that proposed detections actually match data.

### Phase 5: Token-level streaming

**Goal**: ChatGPT-style character-by-character rendering within each iteration.

**Changes**: Switch from `client.messages.create()` to `client.messages.stream()`. Emit SSE `agent_chunk` events. This is independent of the agentic loop and can be done in parallel.

---

## Resolved Design Decisions

1. **New class vs. modified class**: Create `AgenticLLMAgent` rather than modifying `LLMAgent`. Protects the 5 single-shot personas.

2. **Tool-use API vs. regex extraction**: Phase 1 should use the Anthropic tool-use API natively. The model calls `splunk_search` as a structured tool call, not by emitting markdown fences. The orchestrator no longer needs to regex-extract SPL for agentic agents.

3. **Cumulative markdown**: The UI updates the agent's section on every iteration with the latest cumulative markdown. The user sees the investigation unfold in real time.

4. **Downstream agents see final output only**: `depends_on` passes only the final markdown and artifact metadata — not intermediate iterations. Keeps downstream prompts clean.

5. **Viz hints via system prompt**: The agent that generates a search also provides the viz hint, instructed via the system prompt. Future: a search optimizer sub-agent (invoked as a tool call) can refine both SPL and viz hints before execution.

6. **Search timeout**: 30 seconds per search for agentic contexts. The `spl_hunter` is expected to run deeper, more targeted queries that justify the longer wait.

7. **Cost control**: `max_iterations` (stanza-configurable) is the primary cost control mechanism. Future: per-investigation cost budgets configurable in conf.

8. **Provider coupling**: Tool use ties to Anthropic's API shape initially. Accept this. If OpenRouter/OpenAI support is needed, add `complete_with_tools()` to those providers later — the interface is the same, the wire format differs.
