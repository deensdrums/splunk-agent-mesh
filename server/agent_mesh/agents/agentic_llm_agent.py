"""Threat-hunter harness loop driven by the structured event contract.

The threat hunter (spl_hunter) responds with a strict JSON object
``{"events": [...]}`` (see :mod:`.events`). This harness — not Anthropic's
native tool-use — drives the investigation:

  1. Call the model and parse/validate its JSON events.
  2. If the response is malformed, feed back the corrective message and retry.
  3. Render the events to the UI (via ``progress_callback``).
  4. Execute at most ONE external action per turn, taken from the LAST event:
       - ``splunk_search`` -> run the SPL, append results to context, loop.
       - ``handoff``       -> run the reporting sub-agent, append its output to
                              context, loop.
       - ``final`` (or no action event) -> stop.

Driving the loop here (rather than via provider tool-use) keeps it
provider-agnostic and enforces the "one action per turn, no blind search
chains" rule the architecture asks for.
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from ..config import LOG_LLM_IO
from ..investigation_models import now_iso
from ..llm.base import LLMProvider, Message
from ..splunk_client import SplunkClient
from ..tools.splunk_search import run_splunk_search_artifact
from .agent_config import AgentConfig
from .events import (
    ACTION_EVENT_TYPES,
    CORRECTIVE_MESSAGE,
    VIZ_HINT_MAP,
    parse_and_validate,
)

logger = logging.getLogger(__name__)

# Sent to the model after the iteration budget is spent while an action is still
# pending (e.g. a handoff or search landed on the last iteration). It forces a
# closing turn so the reporting output / search results actually reach the user
# instead of the stream dangling on an unresolved action event.
FINALIZE_INSTRUCTION = (
    "You have reached the investigation step limit and cannot run any more searches or handoffs. "
    "Using everything gathered so far (including any reporting-agent output above), respond now with "
    "your closing events ONLY: a result_summary, an optional finding, then a final event. "
    "Do NOT emit splunk_search or handoff events. Remember to always respond with json."
)


def _format_request(request: dict) -> str:
    fields = []
    for key in ("description", "host", "user", "alert_name", "time_range", "dependency_context"):
        value = request.get(key)
        if value:
            fields.append(f"{key}: {value}")
    return "\n".join(fields) if fields else json.dumps(request, indent=2)


def _truncate_rows(rows: list[dict], max_rows: int = 20) -> tuple[list[dict], int]:
    total = len(rows)
    return rows[:max_rows], total


def _truncate_text(text: str, limit: int = 4000) -> str:
    if text is None:
        return "<none>"
    if len(text) <= limit:
        return text
    return f"{text[:limit]}… [truncated {len(text) - limit} chars]"


def _events_to_markdown(events: list[dict]) -> str:
    """Flatten event texts into markdown.

    Kept so anything that still consumes ``output["markdown"]`` (dependency
    context for other agents, demo fallbacks) keeps working; the UI renders the
    structured ``events`` directly.
    """
    parts = []
    for event in events:
        title = event.get("title", "")
        text = event.get("text", "")
        parts.append(f"**{title}**\n\n{text}" if title else text)
    return "\n\n".join(p for p in parts if p)


class AgenticLLMAgent:
    """Threat hunter: an agent that drives an iterative event-based loop."""

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMProvider,
        splunk_client_factory: Callable[[], SplunkClient | None],
        subagents: dict[str, AgentConfig] | None = None,
    ):
        self.config = config
        self.llm = llm
        self.splunk_client_factory = splunk_client_factory
        # Delegated internal capabilities (e.g. the reporting agent), keyed by
        # their configured id. Never surfaced to the UI as peers.
        self.subagents = subagents or {}

    def run(
        self,
        request: dict,
        progress_callback: Callable[[dict, list[dict]], None] | None = None,
    ) -> tuple[dict, list[dict]]:
        """Run the harness loop. Returns (output, artifacts)."""
        started = now_iso()
        messages: list[Message] = [Message(role="user", content=_format_request(request))]
        earliest = request.get("time_range") or "-24h"

        all_artifacts: list[dict] = []
        all_events: list[dict] = []
        model_used = self.config.model
        iteration_count = 0
        terminated_cleanly = False  # True once the model emits a terminal (non-action) turn

        for iteration in range(self.config.max_iterations):
            logger.info(
                "Agent %s: iteration %d/%d",
                self.config.id, iteration + 1, self.config.max_iterations,
            )

            request_messages = [Message(role="system", content=self.config.system_prompt), *messages]
            if LOG_LLM_IO:
                logger.info(
                    "Agent %s: LLM request (iteration %d):\n%s",
                    self.config.id, iteration + 1,
                    "\n".join(f"[{m.role}] {m.content}" for m in request_messages),
                )
            try:
                response = self.llm.complete(
                    messages=request_messages,
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            except Exception as exc:
                logger.exception("Agent %s: LLM call failed at iteration %d.", self.config.id, iteration + 1)
                if all_events:
                    break
                return self._error_output(started, str(exc)), all_artifacts

            model_used = response.model
            if LOG_LLM_IO:
                logger.info(
                    "Agent %s: raw LLM response (iteration %d):\n%s",
                    self.config.id, iteration + 1, response.content,
                )
            events, corrective = parse_and_validate(response.content)

            if corrective:
                # Malformed output: echo it back as the assistant turn, then
                # route the corrective message so the model can retry. The UI
                # never sees this — only validated events reach it. Always log
                # the raw body here (truncated) so the failure is diagnosable.
                logger.warning(
                    "Agent %s: invalid response at iteration %d; retrying. Raw response:\n%s",
                    self.config.id, iteration + 1, _truncate_text(response.content),
                )
                messages.append(Message(role="assistant", content=response.content))
                messages.append(Message(role="user", content=CORRECTIVE_MESSAGE))
                iteration_count += 1
                continue

            assert events is not None
            all_events.extend(events)

            last_event = events[-1]
            action_type = last_event["type"] if last_event["type"] in ACTION_EVENT_TYPES else None

            iteration_artifacts: list[dict] = []
            if action_type == "splunk_search":
                def _search_progress(artifact_update: dict) -> None:
                    self._emit_progress(
                        progress_callback, all_events, [artifact_update], model_used, started, iteration_count,
                    )

                result_payload, artifact = self._execute_search(last_event, earliest, _search_progress)
                if artifact:
                    iteration_artifacts.append(artifact)
                    all_artifacts.append(artifact)
                messages.append(Message(role="assistant", content=response.content))
                messages.append(
                    Message(role="user", content=json.dumps({"splunk_search_result": result_payload}, default=str))
                )
            elif action_type == "handoff":
                handoff_result = self._invoke_subagent(last_event, all_events)
                messages.append(Message(role="assistant", content=response.content))
                messages.append(Message(role="user", content=handoff_result))

            iteration_count += 1
            self._emit_progress(progress_callback, all_events, iteration_artifacts, model_used, started, iteration_count)

            if action_type is None:
                # Last event was final (or purely informational with no action
                # requested): the turn is terminal. Stop without looping.
                terminated_cleanly = True
                logger.info("Agent %s: finished after %d iteration(s).", self.config.id, iteration_count)
                break

        if not terminated_cleanly and all_events:
            # The budget ran out with an action still pending (its results are
            # already in `messages`). Give the model one closing turn so that
            # output — especially a reporting handoff — reaches the user.
            iteration_count = self._finalize_turn(
                messages, all_events, model_used, started, iteration_count, progress_callback,
            )

        # Safety net: never end on a dangling action. If there is still no final
        # event, append a synthetic one so the UI always resolves to a close.
        if all_events and not any(e["type"] == "final" for e in all_events):
            all_events.append(self._synthetic_final())
            iteration_count += 1
            self._emit_progress(progress_callback, all_events, [], model_used, started, iteration_count)

        output = {
            "agent_id": self.config.id,
            "display_name": self.config.display_name,
            "status": "completed",
            "events": all_events,
            "markdown": _events_to_markdown(all_events),
            "model": model_used,
            "started_at": started,
            "completed_at": now_iso(),
            "error": None,
            "_iteration": iteration_count + 1,
        }
        return output, all_artifacts

    def _emit_progress(
        self,
        progress_callback: Callable[[dict, list[dict]], None] | None,
        events: list[dict],
        new_artifacts: list[dict],
        model: str,
        started: str,
        iteration: int,
    ) -> None:
        if not progress_callback:
            return
        progress_callback(
            {
                "agent_id": self.config.id,
                "display_name": self.config.display_name,
                "status": "iterating",
                "events": list(events),
                "markdown": _events_to_markdown(events),
                "model": model,
                "started_at": started,
                "completed_at": None,
                "error": None,
                "_iteration": iteration,
            },
            new_artifacts,
        )

    def _finalize_turn(
        self,
        messages: list[Message],
        all_events: list[dict],
        model_used: str,
        started: str,
        iteration_count: int,
        progress_callback: Callable[[dict, list[dict]], None] | None,
    ) -> int:
        """One closing model turn after the budget is spent.

        Appends only terminal (non-action) events the model returns; any
        splunk_search/handoff it emits despite the instruction is ignored, since
        there is no budget left to execute it. Returns the updated iteration
        count.
        """
        messages.append(Message(role="user", content=FINALIZE_INSTRUCTION))
        try:
            response = self.llm.complete(
                messages=[Message(role="system", content=self.config.system_prompt), *messages],
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        except Exception:
            logger.exception("Agent %s: finalize turn failed.", self.config.id)
            return iteration_count

        events, corrective = parse_and_validate(response.content)
        if corrective or events is None:
            logger.warning("Agent %s: finalize turn returned invalid JSON; using synthetic close.", self.config.id)
            return iteration_count

        terminal = [e for e in events if e["type"] not in ACTION_EVENT_TYPES]
        if not terminal:
            return iteration_count

        all_events.extend(terminal)
        iteration_count += 1
        self._emit_progress(progress_callback, all_events, [], model_used, started, iteration_count)
        return iteration_count

    def _synthetic_final(self) -> dict:
        """A harness-authored final event so the stream never ends on an action."""
        return {
            "type": "final",
            "title": "Investigation incomplete",
            "text": (
                "The investigation reached its step limit before producing a final summary. "
                "Review the findings and searches above; re-run to continue if needed."
            ),
            "payload": {"reason": "max_iterations_reached"},
        }

    def _execute_search(
        self,
        event: dict,
        default_earliest: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> tuple[dict, dict | None]:
        """Execute a splunk_search event's payload. Returns (llm_result, artifact)."""
        payload = event.get("payload", {})
        spl = payload.get("query", "")
        title = event.get("title") or "Search"
        earliest = payload.get("earliest", default_earliest)
        latest = payload.get("latest", "now")
        viz_hint_raw = payload.get("type") or payload.get("viz_hint")
        viz_hint = VIZ_HINT_MAP.get(str(viz_hint_raw).lower()) if viz_hint_raw else None

        logger.info("Agent %s: executing search '%s': %s", self.config.id, title, spl[:120])

        artifact = run_splunk_search_artifact(
            agent_id=self.config.id,
            title=title,
            spl=spl,
            earliest=earliest,
            latest=latest,
            client_factory=self.splunk_client_factory,
            viz_hint=viz_hint,
            timeout_seconds=30.0,
            progress_callback=progress_callback,
        )

        rows = artifact.get("rows", [])
        truncated_rows, total_count = _truncate_rows(rows)
        llm_result: dict = {
            "status": artifact.get("status"),
            "fields": artifact.get("fields", []),
            "rows": truncated_rows,
            "row_count": total_count,
            "sid": artifact.get("sid"),
            "error": artifact.get("error"),
        }
        if total_count > len(truncated_rows):
            llm_result["truncated"] = True
            llm_result["note"] = f"Showing {len(truncated_rows)} of {total_count} total rows."
        return llm_result, artifact

    def _invoke_subagent(self, event: dict, events_so_far: list[dict]) -> str:
        """Run a delegated sub-agent (e.g. reporting) and return text to feed back.

        The sub-agent's output never reaches the UI directly — it is returned
        to the threat hunter, which summarizes it via result_summary/final
        events. This keeps the user-facing stream centered on the threat hunter.
        """
        payload = event.get("payload", {})
        requested = payload.get("sub_agent", "")
        task = payload.get("task", "summarize_findings")
        subagent = self._resolve_subagent(requested)

        if subagent is None:
            logger.warning("Agent %s: no sub-agent available for handoff %r.", self.config.id, requested)
            return (
                "No reporting sub-agent is available. Produce the final answer yourself "
                "as a `final` event. Remember to always respond with json."
            )

        context = (
            f"You are supporting the threat hunter. Task: {task}.\n\n"
            f"Investigation events so far:\n{_events_to_markdown(events_so_far)}"
        )
        try:
            response = self.llm.complete(
                messages=[
                    Message(role="system", content=subagent.system_prompt),
                    Message(role="user", content=context),
                ],
                model=subagent.model,
                temperature=subagent.temperature,
                max_tokens=subagent.max_tokens,
            )
            report = response.content
        except Exception as exc:
            logger.exception("Sub-agent %s failed during handoff.", subagent.id)
            return (
                f"The reporting sub-agent failed: {exc}. Produce the final answer yourself "
                "as a `final` event. Remember to always respond with json."
            )

        return (
            f"The reporting sub-agent ({subagent.id}) returned the following report:\n\n"
            f"{report}\n\n"
            "Summarize this for the user using a `result_summary` event and then a `final` event. "
            "Remember to always respond with json."
        )

    def _resolve_subagent(self, requested: str) -> AgentConfig | None:
        """Resolve a handoff target. Exact id match, else the sole sub-agent."""
        if requested and requested in self.subagents:
            return self.subagents[requested]
        if len(self.subagents) == 1:
            return next(iter(self.subagents.values()))
        return None

    def _error_output(self, started: str, error: str) -> dict:
        return {
            "agent_id": self.config.id,
            "display_name": self.config.display_name,
            "status": "error",
            "events": [],
            "markdown": f"_Agent failed: {error}_",
            "model": self.config.model,
            "started_at": started,
            "completed_at": now_iso(),
            "error": error,
        }
