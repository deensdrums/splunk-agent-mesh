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
    def __init__(self):
        self.searches: list[dict] = []

    def run_search(self, spl, earliest="-24h", latest="now", **kwargs):
        self.searches.append({"spl": spl, "earliest": earliest, "latest": latest, "kwargs": kwargs})
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


def _captured_phases(agent: AgenticLLMAgent) -> list:
    phases: list = []
    agent.run({"description": "x"}, progress_callback=lambda output, _artifacts: phases.append(output.get("phase")))
    return phases


def test_handoff_emits_delegating_before_finalizing():
    handoff = _envelope(
        {"type": "narration", "title": "Found it", "text": "compromise", "payload": {}},
        {"type": "handoff", "title": "Report", "text": "go",
         "payload": {"sub_agent": "executive_brief", "task": "summarize_findings"}},
    )
    final = _envelope(
        {"type": "result_summary", "title": "Report", "text": "summarized", "payload": {}},
        {"type": "final", "title": "Done", "text": "final", "payload": {}},
    )
    llm = FakeLLM([handoff, "## Executive summary\nHigh severity.", final])
    reporting = _config(id="executive_brief", agent_role="subagent", agent_mode="single_shot")
    agent = AgenticLLMAgent(_config(), llm, lambda: None, {"executive_brief": reporting})

    phases = _captured_phases(agent)

    # "delegating" surfaces before the blocking sub-agent call; "finalizing"
    # after it (while the threat hunter writes the summary).
    assert "delegating" in phases
    assert "finalizing" in phases
    assert phases.index("delegating") < phases.index("finalizing")


def test_search_turn_emits_interpreting_phase():
    search = _envelope(
        {"type": "narration", "title": "Start", "text": "looking", "payload": {}},
        {"type": "splunk_search", "title": "Logins", "text": "checking",
         "payload": {"query": "index=auth | stats count", "type": "table"}},
    )
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    llm = FakeLLM([search, final])
    agent = AgenticLLMAgent(_config(), llm, lambda: FakeSplunk())

    assert "interpreting" in _captured_phases(agent)


def test_search_optimizer_runs_before_splunk_search_and_context_keeps_both_queries():
    search = _envelope(
        {"type": "splunk_search", "title": "Auth", "text": "checking",
         "payload": {"query": "index=auth action=failure | stats count by user", "type": "table"}},
    )
    optimizer = json.dumps({
        "optimized_query": "index=auth action=failure user=* | stats count by user",
        "changes": ["Added user=* to constrain the stats input to populated user values."],
        "semantic_equivalence": "equivalent",
        "risk": "low",
        "warnings": [],
    })
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    llm = FakeLLM([search, optimizer, final])
    splunk = FakeSplunk()
    search_optimizer = _config(
        id="search_optimizer",
        agent_role="subagent",
        subagent_kind="search_optimizer",
        invoke_policy="before_search",
        output_contract="json",
    )

    agent = AgenticLLMAgent(_config(), llm, lambda: splunk, {"search_optimizer": search_optimizer})
    _, artifacts = agent.run({"description": "investigate auth"})

    assert splunk.searches[0]["spl"] == "index=auth action=failure user=* | stats count by user"
    assert artifacts[0]["requested_spl"] == "index=auth action=failure | stats count by user"
    assert artifacts[0]["executed_spl"] == "index=auth action=failure user=* | stats count by user"
    assert artifacts[0]["optimization"]["applied"] is True
    result_messages = [m.content for m in llm.calls[2] if m.role == "user" and "splunk_search_result" in m.content]
    result_payload = json.loads(result_messages[-1])["splunk_search_result"]
    assert result_payload["requested_query"] == "index=auth action=failure | stats count by user"
    assert result_payload["executed_query"] == "index=auth action=failure user=* | stats count by user"


def test_search_optimizer_rejects_unsafe_query_and_runs_original_search():
    search = _envelope(
        {"type": "splunk_search", "title": "Auth", "text": "checking",
         "payload": {"query": "index=auth action=failure | stats count", "type": "single"}},
    )
    unsafe_optimizer = json.dumps({
        "optimized_query": "index=auth action=failure | delete",
        "changes": ["bad"],
        "semantic_equivalence": "equivalent",
        "risk": "low",
        "warnings": ["contains destructive command"],
    })
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    llm = FakeLLM([search, unsafe_optimizer, final])
    splunk = FakeSplunk()
    search_optimizer = _config(
        id="search_optimizer",
        agent_role="subagent",
        subagent_kind="search_optimizer",
        invoke_policy="before_search",
        output_contract="json",
    )

    agent = AgenticLLMAgent(_config(), llm, lambda: splunk, {"search_optimizer": search_optimizer})
    _, artifacts = agent.run({"description": "investigate auth"})

    assert splunk.searches[0]["spl"] == "index=auth action=failure | stats count"
    assert artifacts[0]["optimization"]["applied"] is False
    assert artifacts[0]["optimization"]["reason"] == "optimizer_rejected"
    assert artifacts[0]["optimization"]["proposed_query"] == "index=auth action=failure | delete"


def test_after_final_reporting_subagent_runs_without_handoff():
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    llm = FakeLLM([final, "## Executive summary\nNo confirmed compromise."])
    reporting = _config(
        id="executive_brief",
        agent_role="subagent",
        subagent_kind="report",
        invoke_policy="after_final",
    )

    agent = AgenticLLMAgent(_config(), llm, lambda: None, {"executive_brief": reporting})
    output, _ = agent.run({"description": "x"})

    assert [e["type"] for e in output["events"]] == ["result_summary", "final"]
    assert output["events"][0]["payload"]["subagent_id"] == "executive_brief"
    assert len(llm.calls) == 2


def test_after_final_labeler_emits_structured_finding():
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    label = json.dumps({
        "label": "false_positive",
        "confidence": 0.82,
        "severity": "low",
        "rubric_scores": {"malicious_evidence": 1, "benign_explanation": 4},
        "rationale": "The observed activity matches expected administrative behavior.",
        "counter_evidence": ["No lateral movement or suspicious process activity was found."],
        "recommended_disposition": "Close as false positive after analyst review.",
    })
    llm = FakeLLM([final, label])
    labeler = _config(
        id="event_labeler",
        agent_role="subagent",
        subagent_kind="labeler",
        invoke_policy="after_final",
        output_contract="json",
    )

    agent = AgenticLLMAgent(_config(), llm, lambda: None, {"event_labeler": labeler})
    output, _ = agent.run({"description": "x"})

    assert [e["type"] for e in output["events"]] == ["finding", "final"]
    finding = output["events"][0]
    assert finding["payload"]["subagent_id"] == "event_labeler"
    assert finding["payload"]["label"] == "false_positive"
    assert finding["payload"]["confidence"] == 0.82


def test_after_final_labeler_accepts_fenced_json_response():
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    label = json.dumps({
        "label": "needs_review",
        "confidence": 0.71,
        "severity": "medium",
        "rubric_scores": {"suspicious_evidence": 3, "benign_explanation": 1},
        "rationale": "The available evidence requires analyst review.",
        "counter_evidence": ["No successful follow-on activity was observed."],
        "recommended_disposition": "Review account owner and source context.",
    })
    llm = FakeLLM([final, f"```json\n{label}\n```"])
    labeler = _config(
        id="event_labeler",
        agent_role="subagent",
        subagent_kind="labeler",
        invoke_policy="after_final",
        output_contract="json",
    )

    agent = AgenticLLMAgent(_config(), llm, lambda: None, {"event_labeler": labeler})
    output, _ = agent.run({"description": "x"})

    assert [e["type"] for e in output["events"]] == ["finding", "final"]
    assert output["events"][0]["payload"]["label"] == "needs_review"


def test_after_final_labeler_retries_after_invalid_json():
    final = _envelope({"type": "final", "title": "Done", "text": "summary", "payload": {}})
    label = json.dumps({
        "label": "insufficient_evidence",
        "confidence": 0.9,
        "severity": "unknown",
        "rubric_scores": {"data_quality": 1},
        "rationale": "The run lacks enough telemetry to classify the alert.",
        "counter_evidence": [],
        "recommended_disposition": "Improve telemetry and rerun the investigation.",
    })
    llm = FakeLLM([final, "Here is my classification:", label])
    labeler = _config(
        id="event_labeler",
        agent_role="subagent",
        subagent_kind="labeler",
        invoke_policy="after_final",
        output_contract="json",
    )

    agent = AgenticLLMAgent(_config(), llm, lambda: None, {"event_labeler": labeler})
    output, _ = agent.run({"description": "x"})

    assert [e["type"] for e in output["events"]] == ["finding", "final"]
    assert output["events"][0]["payload"]["label"] == "insufficient_evidence"
    assert len(llm.calls) == 3
    assert any("previous response was not valid JSON" in m.content for m in llm.calls[2] if m.role == "user")
