"""Agentic LLM agent with iterative tool-use loop.

Unlike the single-shot LLMAgent, this agent uses the Anthropic tool-use API
to iteratively search Splunk, observe results, and refine its investigation.
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from ..investigation_models import now_iso
from ..llm.anthropic_provider import AnthropicProvider
from ..llm.base import ToolCall
from ..splunk_client import SplunkClient
from ..tools.splunk_search import run_splunk_search_artifact
from .agent_config import AgentConfig

logger = logging.getLogger(__name__)

_VIZ_HINT_MAP: dict[str, str] = {
    "column": "timechart",
    "timechart": "timechart",
    "line": "line",
    "pie": "pie",
    "bar": "bar",
    "table": "table",
    "single": "single",
}

SPLUNK_SEARCH_TOOL = {
    "name": "splunk_search",
    "description": (
        "Execute a SPL search against Splunk and return results. "
        "Use this to investigate incidents, validate hypotheses, and gather evidence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "spl": {
                "type": "string",
                "description": "The SPL query to execute.",
            },
            "earliest": {
                "type": "string",
                "description": "Earliest time (e.g., '-24h', '-7d'). Defaults to the investigation time range.",
            },
            "latest": {
                "type": "string",
                "description": "Latest time (e.g., 'now'). Defaults to 'now'.",
            },
            "viz_hint": {
                "type": "string",
                "enum": ["timechart", "line", "pie", "bar", "table", "single"],
                "description": "Visualization hint for chart rendering.",
            },
            "title": {
                "type": "string",
                "description": "Short title describing what this search investigates.",
            },
        },
        "required": ["spl", "title"],
    },
}


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


class AgenticLLMAgent:
    """Agent that iteratively uses tools to investigate."""

    def __init__(
        self,
        config: AgentConfig,
        llm: AnthropicProvider,
        splunk_client_factory: Callable[[], SplunkClient | None],
    ):
        self.config = config
        self.llm = llm
        self.splunk_client_factory = splunk_client_factory

    def run(
        self,
        request: dict,
        progress_callback: Callable[[dict, list[dict]], None] | None = None,
    ) -> tuple[dict, list[dict]]:
        """Run the agentic loop. Returns (output, artifacts)."""
        started = now_iso()
        user_msg = _format_request(request)
        messages: list[dict] = [{"role": "user", "content": user_msg}]
        tools = [SPLUNK_SEARCH_TOOL]
        earliest = request.get("time_range") or "-24h"

        all_artifacts: list[dict] = []
        text_parts: list[str] = []
        total_input_tokens = 0
        total_output_tokens = 0
        model_used = self.config.model
        iteration_count = 0

        for iteration in range(self.config.max_iterations):
            logger.info(
                "Agent %s: iteration %d/%d",
                self.config.id, iteration + 1, self.config.max_iterations,
            )

            try:
                response = self.llm.complete_with_tools(
                    messages=messages,
                    tools=tools,
                    system=self.config.system_prompt,
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            except Exception as exc:
                logger.exception(
                    "Agent %s: LLM call failed at iteration %d.",
                    self.config.id, iteration + 1,
                )
                if text_parts:
                    text_parts.append(f"\n\n_Investigation interrupted: {exc}_")
                    break
                return self._error_output(started, str(exc)), all_artifacts

            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens
            model_used = response.model

            if response.content_text:
                text_parts.append(response.content_text)

            if response.stop_reason != "tool_use" or not response.tool_calls:
                logger.info(
                    "Agent %s: finished after %d iteration(s) (%d tool calls total).",
                    self.config.id, iteration + 1, len(all_artifacts),
                )
                break

            messages.append({"role": "assistant", "content": response.raw_content})

            tool_results = []
            iteration_artifacts = []
            for tool_call in response.tool_calls:
                if tool_call.name == "splunk_search":
                    result_payload, artifact = self._execute_search(tool_call, earliest)
                    if artifact:
                        iteration_artifacts.append(artifact)
                        all_artifacts.append(artifact)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(result_payload, default=str),
                    })
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps({"error": f"Unknown tool: {tool_call.name}"}),
                        "is_error": True,
                    })

            messages.append({"role": "user", "content": tool_results})
            iteration_count += 1

            if progress_callback:
                progress_callback(
                    {
                        "agent_id": self.config.id,
                        "display_name": self.config.display_name,
                        "status": "iterating",
                        "markdown": "\n\n".join(text_parts),
                        "model": model_used,
                        "started_at": started,
                        "completed_at": None,
                        "error": None,
                        "_iteration": iteration_count,
                    },
                    iteration_artifacts,
                )

        markdown = "\n\n".join(text_parts)
        output = {
            "agent_id": self.config.id,
            "display_name": self.config.display_name,
            "status": "completed",
            "markdown": markdown,
            "model": model_used,
            "started_at": started,
            "completed_at": now_iso(),
            "error": None,
            "_iteration": iteration_count + 1,
        }
        return output, all_artifacts

    def _execute_search(
        self,
        tool_call: ToolCall,
        default_earliest: str,
    ) -> tuple[dict, dict | None]:
        """Execute a splunk_search tool call. Returns (llm_result, artifact)."""
        spl = tool_call.input.get("spl", "")
        title = tool_call.input.get("title", "Search")
        earliest = tool_call.input.get("earliest", default_earliest)
        latest = tool_call.input.get("latest", "now")
        viz_hint_raw = tool_call.input.get("viz_hint")
        viz_hint = _VIZ_HINT_MAP.get(viz_hint_raw) if viz_hint_raw else None

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

    def _error_output(self, started: str, error: str) -> dict:
        return {
            "agent_id": self.config.id,
            "display_name": self.config.display_name,
            "status": "error",
            "markdown": f"_Agent failed: {error}_",
            "model": self.config.model,
            "started_at": started,
            "completed_at": now_iso(),
            "error": error,
        }
