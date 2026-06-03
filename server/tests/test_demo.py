"""Smoke tests for the deterministic demo replay (DEMO-003)."""

from __future__ import annotations

import time

from agent_mesh.agents.agent_config import AgentConfig
from agent_mesh.agents.orchestrator import Orchestrator
from agent_mesh.conf_reader import ConfReader
from agent_mesh.demo.demo_case import build_demo_result
from agent_mesh.job_store import InvestigationJobStore
from agent_mesh.request_context import RequestContext


def _cfg() -> AgentConfig:
    return AgentConfig(
        id="spl_hunter",
        display_name="Threat Hunter",
        description="",
        system_prompt="demo",
        model="claude-haiku-4-5-20251001",
        agent_mode="agentic",
        agent_role="primary",
    )


class _StubConf(ConfReader):
    def get_agents(self) -> list[AgentConfig]:
        return [_cfg()]


# ---- content: no LLM call, representative timeline, chart rows --------------

def test_demo_sync_result_has_timeline_and_chart_rows():
    result = build_demo_result([_cfg()])  # no progress_callback -> instant

    assert result["status"] == "complete"
    out = result["agents"]["spl_hunter"]
    types = [e["type"] for e in out["events"]]
    # A representative investigation timeline.
    for required in ("narration", "splunk_search", "finding", "handoff", "final"):
        assert required in types, f"demo timeline missing {required}"

    # At least one chart artifact with guaranteed rows.
    charts = [a for a in result["artifacts"]
              if a["status"] == "done" and a["visualization"]["kind"] != "table" and a["rows"]]
    assert charts, "expected at least one completed chart artifact with rows"
    assert all(a["sid"] == "demo" for a in result["artifacts"])  # browser keeps rows, no Splunk poll


# ---- replay: progressive emission, pending -> running -> done ---------------

def test_demo_replay_emits_progressively(monkeypatch):
    monkeypatch.setenv("AGENT_MESH_DEMO_STEP_SECONDS", "0")
    updates: list[dict] = []
    build_demo_result([_cfg()], progress_callback=updates.append)

    # More updates than events (searches emit pending/running/done).
    assert len(updates) > 5

    # The first search artifact moves pending -> running -> done with rising revisions.
    jndi = [a for u in updates for a in u["artifacts"] if a["id"] == "artifact-demo-jndi"]
    statuses = [a["status"] for a in jndi]
    assert statuses[0] == "pending" and statuses[-1] == "done"
    revisions = [a["_revision"] for a in jndi]
    assert revisions == sorted(revisions) and len(set(revisions)) == len(revisions)

    # Phases surface so the UI can label the working indicator (incl. the
    # sub-agent window the UI cannot otherwise observe).
    phases = {u["agents"]["spl_hunter"].get("phase") for u in updates}
    assert "delegating" in phases
    assert "interpreting" in phases

    # The final emitted snapshot carries the complete timeline.
    final_events = updates[-1]["agents"]["spl_hunter"]["events"]
    assert final_events[-1]["type"] == "final"


# ---- integration: start -> completion -> artifact (the SSE path's source) ---

def test_demo_runs_through_job_store_to_completion(monkeypatch):
    monkeypatch.setenv("AGENT_MESH_DEMO_STEP_SECONDS", "0")
    store = InvestigationJobStore()
    context = RequestContext(username="judge")

    def runner(payload, ctx, investigation_id, progress_callback):
        orchestrator = Orchestrator(conf_reader=_StubConf(), context=ctx)
        return orchestrator.run(payload, investigation_id=investigation_id, progress_callback=progress_callback)

    job = store.create({"description": "demo", "demo": True}, context, runner)

    deadline = time.time() + 10
    while time.time() < deadline:
        current = store.get(job["id"])
        if current and current["status"] not in ("running", "pending"):
            break
        time.sleep(0.02)

    final = store.get(job["id"])
    assert final is not None and final["status"] == "complete"
    out = final["agents"]["spl_hunter"]
    assert out["status"] == "completed"
    assert any(e["type"] == "final" for e in out["events"])
    artifacts = [a for a in final["artifacts"] if a["type"] == "splunk_search"]
    assert any(a["status"] == "done" and a["rows"] for a in artifacts)


def test_demo_makes_no_llm_call():
    # No LLM provider configured; demo must still complete (it never calls one).
    orchestrator = Orchestrator(conf_reader=_StubConf(), llm_provider=None)
    result = orchestrator.run({"description": "demo", "demo": True})
    assert result["status"] == "complete"
    assert result["agents"]["spl_hunter"]["events"]
