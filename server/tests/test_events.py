"""Tests for the structured event schema/validator and the harness loop."""

from __future__ import annotations

import json

from agent_mesh.agents.agent_config import AgentConfig
from agent_mesh.agents.agentic_llm_agent import AgenticLLMAgent
from agent_mesh.agents.events import CORRECTIVE_MESSAGE, parse_and_validate
from agent_mesh.llm.base import CompletionResponse, Message
from agent_mesh.splunk_client import SearchResult


# ---- Schema validation ----------------------------------------------------

def _envelope(*events: dict) -> str:
    return json.dumps({"events": list(events)})


def test_valid_envelope_parses():
    raw = _envelope(
        {"type": "narration", "title": "Hi", "text": "starting", "payload": {}},
        {"type": "final", "title": "Done", "text": "done", "payload": {"summary": "x"}},
    )
    events, corrective = parse_and_validate(raw)
    assert corrective is None
    assert events is not None
    assert [e["type"] for e in events] == ["narration", "final"]


def test_json_fence_is_stripped():
    inner = '{"type": "final", "title": "Done", "text": "x", "payload": {}}'
    raw = f"```json\n{{\"events\": [{inner}]}}\n```"
    events, corrective = parse_and_validate(raw)
    assert corrective is None
    assert events is not None and events[0]["type"] == "final"


def test_bare_fence_without_language_is_stripped():
    raw = '```\n{"events": [{"type": "narration", "title": "t", "text": "x", "payload": {}}]}\n```'
    events, corrective = parse_and_validate(raw)
    assert corrective is None and events is not None


def test_bare_json_still_parses_unchanged():
    raw = _envelope({"type": "narration", "title": "t", "text": "x", "payload": {}})
    events, corrective = parse_and_validate(raw)
    assert corrective is None and events is not None


def test_non_json_routes_corrective():
    events, corrective = parse_and_validate("Here is my answer, not JSON.")
    assert events is None
    assert corrective == CORRECTIVE_MESSAGE


def test_top_level_array_rejected():
    events, corrective = parse_and_validate('[{"type": "final", "title": "t", "text": "x", "payload": {}}]')
    assert events is None and corrective == CORRECTIVE_MESSAGE


def test_missing_events_key_rejected():
    events, corrective = parse_and_validate('{"foo": []}')
    assert events is None and corrective == CORRECTIVE_MESSAGE


def test_empty_events_rejected():
    events, corrective = parse_and_validate('{"events": []}')
    assert events is None and corrective == CORRECTIVE_MESSAGE


def test_invalid_type_rejected():
    raw = _envelope({"type": "bogus", "title": "t", "text": "x", "payload": {}})
    events, corrective = parse_and_validate(raw)
    assert events is None and corrective == CORRECTIVE_MESSAGE


def test_payload_as_array_rejected():
    raw = _envelope({"type": "finding", "title": "t", "text": "x", "payload": []})
    events, corrective = parse_and_validate(raw)
    assert events is None and corrective == CORRECTIVE_MESSAGE


def test_non_string_title_rejected():
    raw = _envelope({"type": "narration", "title": 5, "text": "x", "payload": {}})
    events, corrective = parse_and_validate(raw)
    assert events is None and corrective == CORRECTIVE_MESSAGE


# ---- Harness loop ----------------------------------------------------------

class FakeLLM:
    """Returns scripted completions in order; records messages it received."""

    def __init__(self, scripted: list[str]):
        self.scripted = scripted
        self.calls: list[list[Message]] = []

    def complete(self, messages, model=None, temperature=0.2, max_tokens=2048):
        self.calls.append(list(messages))
        content = self.scripted[min(len(self.calls) - 1, len(self.scripted) - 1)]
        return CompletionResponse(content=content, model=model or "fake", input_tokens=1, output_tokens=1)

    def test_connection(self):
        return {"success": True}


class FakeSplunk:
    def run_search(self, spl, earliest="-24h", latest="now", **kwargs):
        return SearchResult(
            spl=spl,
            sid="sid-1",
            status="done",
            fields=["user", "count"],
            events=[{"user": "jdoe", "count": "184"}],
        )


def _config(**overrides) -> AgentConfig:
    base = dict(
        id="spl_hunter",
        display_name="Threat Hunter",
        description="",
        system_prompt="be a threat hunter",
        agent_mode="agentic",
        max_iterations=5,
    )
    base.update(overrides)
    return AgentConfig(**base)


def test_loop_executes_search_then_final():
    search = _envelope(
        {"type": "narration", "title": "Start", "text": "looking", "payload": {}},
        {
            "type": "splunk_search",
            "title": "Failed logins",
            "text": "checking",
            "payload": {"query": "index=auth action=failure | stats count by user", "type": "table"},
        },
    )
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    llm = FakeLLM([search, final])

    agent = AgenticLLMAgent(_config(), llm, lambda: FakeSplunk())
    output, artifacts = agent.run({"description": "investigate auth"})

    assert output["status"] == "completed"
    assert [e["type"] for e in output["events"]] == ["narration", "splunk_search", "final"]
    assert len(artifacts) == 1
    assert artifacts[0]["status"] == "done"
    # Two LLM calls: initial + after search results fed back.
    assert len(llm.calls) == 2


def test_loop_emits_pending_search_artifact_before_final_results():
    search = _envelope(
        {
            "type": "splunk_search",
            "title": "Failed logins",
            "text": "checking",
            "payload": {"query": "index=auth action=failure | stats count by user", "type": "table"},
        },
    )
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    updates = []

    agent = AgenticLLMAgent(_config(), FakeLLM([search, final]), lambda: FakeSplunk())
    agent.run({"description": "investigate auth"}, progress_callback=lambda output, artifacts: updates.extend(artifacts))

    assert [artifact["status"] for artifact in updates[:2]] == ["pending", "done"]
    assert updates[0]["id"] == updates[1]["id"]
    assert updates[0]["_revision"] < updates[1]["_revision"]


def test_loop_recovers_from_malformed_then_finishes():
    final = _envelope({"type": "final", "title": "Done", "text": "ok", "payload": {}})
    llm = FakeLLM(["not json at all", final])

    agent = AgenticLLMAgent(_config(), llm, lambda: None)
    output, _ = agent.run({"description": "x"})

    assert output["status"] == "completed"
    assert [e["type"] for e in output["events"]] == ["final"]
    # The corrective message was routed back as a user turn before the retry.
    assert any(
        m.role == "user" and m.content == CORRECTIVE_MESSAGE for m in llm.calls[1]
    )


def test_handoff_on_last_iteration_gets_finalize_turn():
    # max_iterations=1: the hunter hands off on its only iteration, so the
    # summarizing turn must come from the post-loop finalize turn instead.
    handoff = _envelope(
        {"type": "narration", "title": "Found it", "text": "compromise", "payload": {}},
        {
            "type": "handoff",
            "title": "Report please",
            "text": "delegating",
            "payload": {"sub_agent": "executive_brief", "task": "summarize_findings"},
        },
    )
    final = _envelope(
        {"type": "result_summary", "title": "Report", "text": "summarized", "payload": {}},
        {"type": "final", "title": "Done", "text": "final", "payload": {}},
    )
    # Call 1: hunter -> handoff. Call 2: reporting sub-agent. Call 3: finalize turn.
    llm = FakeLLM([handoff, "## Executive summary\nHigh severity.", final])
    reporting = _config(id="executive_brief", agent_role="subagent", agent_mode="single_shot")
    agent = AgenticLLMAgent(_config(max_iterations=1), llm, lambda: None, {"executive_brief": reporting})
    output, _ = agent.run({"description": "x"})

    assert [e["type"] for e in output["events"]] == ["narration", "handoff", "result_summary", "final"]
    assert len(llm.calls) == 3
    # The finalize turn received the budget-limit instruction.
    assert any("step limit" in m.content for m in llm.calls[2] if m.role == "user")


def test_synthetic_final_when_budget_exhausted_on_search():
    # The only response is a search; with max_iterations=1 there is no turn to
    # interpret results, and the finalize turn also yields no terminal events,
    # so the harness appends a synthetic final.
    search = _envelope(
        {
            "type": "splunk_search",
            "title": "Logins",
            "text": "checking",
            "payload": {"query": "index=auth | stats count", "type": "table"},
        }
    )
    # Finalize turn returns only another (ignored) action -> synthetic close.
    llm = FakeLLM([search, search])
    agent = AgenticLLMAgent(_config(max_iterations=1), llm, lambda: FakeSplunk())
    output, _ = agent.run({"description": "x"})

    types = [e["type"] for e in output["events"]]
    assert types[0] == "splunk_search"
    assert types[-1] == "final"
    assert output["events"][-1]["payload"].get("reason") == "max_iterations_reached"


def test_handoff_invokes_subagent_then_threat_hunter_summarizes():
    handoff = _envelope(
        {"type": "narration", "title": "Found it", "text": "compromise", "payload": {}},
        {
            "type": "handoff",
            "title": "Report please",
            "text": "delegating",
            "payload": {"sub_agent": "executive_brief", "task": "summarize_findings"},
        },
    )
    final = _envelope(
        {"type": "result_summary", "title": "Report", "text": "summarized", "payload": {}},
        {"type": "final", "title": "Done", "text": "final", "payload": {}},
    )
    # Call 1: threat hunter -> handoff. Call 2: reporting sub-agent (markdown).
    # Call 3: threat hunter -> result_summary + final.
    llm = FakeLLM([handoff, "## Executive summary\nHigh severity.", final])

    reporting = _config(id="executive_brief", display_name="Reporting", agent_role="subagent", agent_mode="single_shot")
    agent = AgenticLLMAgent(_config(), llm, lambda: None, {"executive_brief": reporting})
    output, _ = agent.run({"description": "x"})

    assert [e["type"] for e in output["events"]] == ["narration", "handoff", "result_summary", "final"]
    assert len(llm.calls) == 3
