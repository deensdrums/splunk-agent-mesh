# Slop Cleanup — Review Findings

A "slop review" of the codebase: severe anti-patterns, LLM-smell / dead code,
and clear simplification opportunities. Findings only — nothing here has been
refactored. File/line references are approximate where the code shifts.

Excluded by request: the pervasive passing of the user's Splunk token (already
known).

> **Status (2026-06-01):** B6 and B7 are **resolved** — the dead native-tool-use
> path, the single-shot / `depends_on` DAG / fenced-SPL machinery, and the five
> retired SOC stanzas were deleted (and C11 fell out with them). See ADR-019 in
> `docs/DECISIONS.md`. The remaining items below are still open.

Overall read: the bones are sound (event contract, harness loop, provider
abstraction). The mess is mostly accreted dead alternatives and un-DRY'd
helpers, not bad architecture. Highest-impact items: A1, A2, A3, and deleting
the two dead paths (B6, B7).

---

## A. Severe anti-patterns

**A1. `GET /settings` does a network round-trip to return a boolean.**
`app.py` `get_settings` → `store.api_key_configured()` (`settings_store.py:71`)
→ `get_api_key()` → on the Splunk path that's a synchronous `httpx.GET` to the
Passwords API (`settings_store.py:205-228`). A trivial "is a key configured?"
call blocks on Splunk REST, and `api_key_configured` wraps it in a blanket
`except Exception: return False` (`settings_store.py:74`) — expensive and
silently lies on error.

**A2. Functions defined inside loops with closure-capture hacks.**
`orchestrator.py:94` defines `_iteration_cb` per loop iteration and smuggles the
loop variable via the `_cfg_id=cfg.id` default-arg trick — the textbook
late-binding-closure smell. Same pattern at `agentic_llm_agent.py:180`
(`def _search_progress` redefined every search turn). Both should be
methods / `functools.partial`.

**A3. Silent `except Exception` swallowing.**
`settings_store.py:34` (`_load_local_settings` → `return {}`),
`settings_store.py:74`, and the job boundary at `job_store.py:127`. Config
corruption, auth failures, and key-read errors all vanish into empty dicts /
`False` with no signal.

**A4. Type annotations that lie.**
`job_store.py:112` (`_run`) declares its `runner` as
`Callable[[dict, RequestContext, str], dict]`, but it is created as a 4-arg
callable (`job_store.py:33`) and invoked with 4 args (`job_store.py:115`).

**A5. `get()` shallow-copies and pretends it's safe.**
`job_store.py:64` returns `dict(job)` — the nested `agents` / `artifacts` are
still shared references handed to the SSE reader while worker threads mutate
them elsewhere. Reads as defensive but isn't a real copy.

---

## B. LLM smell / dead code

**B6. The abandoned native-tool-use path is dead but still shipped.**
`complete_with_tools` (`anthropic_provider.py:55`), plus `ToolCall` /
`ToolUseResponse` (`base.py:22,29`), are defined and referenced only within
themselves — the harness never calls them (no import in
`agentic_llm_agent.py`). Pure carrying cost from the pre-event-loop design.

**B7. The single-shot / fenced-SPL / `depends_on` machinery is unreachable.**
`extract_spl_blocks` (`splunk_search.py:32`), `orchestrator._run_agent_tools`
(`orchestrator.py:208`), and the DAG (`_execution_order`,
`_dependency_context`) only fire for non-agentic agents — and the shipping mesh
has exactly one agentic agent. Documented as "retained," but it is a large
amount of live-looking code that nothing exercises.

**B8. Dead constants / methods / components.**
`EVENT_TYPES` (`events.py:44`) is never used — the `Literal[...]` in
`AgentEvent` is the real validator. `_default_model` is defined 4× (`base.py:59`
plus all three providers) and called nowhere. `AgentTabsPanel.tsx` (115 lines)
is exported but imported nowhere.

**B9. Comments — mostly fine, with a narration tic.**
The comments are above typical slop; the issue is volume, not correctness. A few
are pure restatement (e.g. `agentic_llm_agent.py:198-200`, "The phase describes
what the agent will do next…" over self-evident code). Not worth a pass on its
own.

---

## C. Sane simplification (dedup / flatten)

**C10. `renderViz` is three copy-pasted chart blocks.**
`ArtifactRenderer.tsx:188-240` — the `timechart` / `line` / `pie` branches are
identical except the component and width/height. A
`{ timechart: Column, line: Line, pie: Pie }` lookup + one render collapses
~50 lines to ~15.

**C11. Duplicated viz-hint map.**
`splunk_search.py:21` (`_VIZ_HINT_MAP`) and `events.py:62` (`VIZ_HINT_MAP`) are
the same `column→timechart…` dict maintained in two files. One should import the
other.

**C12. The "AgentOutput" dict is hand-built in ~5 places with no factory.**
`llm_agent.py:62` and `:76` (`_error_output`), `agentic_llm_agent.py` (success
output, `_error_output:437`, synthetic-final), and `demo_case.py`. The same
shape is also duplicated front-end in `demoData.ts`. One constructor (or a
dataclass) would kill a class of drift bugs.

**C13. Copy-pasted helpers across the two agents / providers.**
`_format_request` exists verbatim in `llm_agent.py:24` and
`agentic_llm_agent.py:54`. `now_iso` (`investigation_models.py:13`) vs
`_now_iso` (`llm_agent.py:20`) are two implementations of one thing.
`test_connection` is identical in `anthropic_provider.py:111` and
`openai_compatible_provider.py:48` — push it to `base.py` (the OpenRouter ⊂
OpenAICompatible subclassing already proves the pattern).

**C14. Front-end SSE handlers duplicated.**
`InvestigationPage.tsx` `onAgentComplete` (~129-149) and `onAgentUpdate`
(~150-161) share the same setResult / artifact-merge body — extract one merge
helper.

---

## Suggested order of attack

1. Delete dead paths (B6, B7, B8) — biggest "looks load-bearing, isn't"
   reduction, and it shrinks the surface for C12/C13.
2. Fix the silent-failure / network-for-a-bool issues (A1, A3) — these cause
   confusing demo behavior.
3. Hoist the loop closures (A2).
4. DRY the duplicated helpers, maps, and render branches (C10–C14).
