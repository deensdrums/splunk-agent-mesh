"""Harness-managed request/response sub-agent calls.

Sub-agents are configured in agents.conf, but not all of them should depend on
the primary model remembering to emit a handoff. This module runs deterministic
lifecycle calls such as search optimization, reporting, and labeling.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..llm.base import LLMProvider, Message
from .agent_config import AgentConfig

logger = logging.getLogger(__name__)

_SPL_DANGEROUS_RE = re.compile(
    r"\|\s*(delete|outputlookup|collect|script|sendemail|map|rest|dbxquery)\b",
    re.IGNORECASE,
)
_CODE_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)

_LABEL_JSON_TEMPLATE = {
    "label": "needs_review",
    "confidence": 0.0,
    "severity": "unknown",
    "rubric_scores": {
        "malicious_evidence": 0,
        "benign_explanation": 0,
        "data_quality": 0,
    },
    "rationale": "One concise evidence-based rationale.",
    "counter_evidence": [],
    "recommended_disposition": "One concise disposition for the analyst.",
}

_LABEL_CORRECTIVE_MESSAGE = (
    "Your previous response was not valid JSON for the required schema. "
    "Return only one JSON object. Do not include Markdown, code fences, comments, or explanatory text."
)


class SearchOptimizationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optimized_query: str = Field(min_length=1)
    changes: list[str] = Field(default_factory=list)
    semantic_equivalence: Literal["same_intent", "equivalent", "changed"] = "same_intent"
    risk: Literal["low", "medium", "high"] = "low"
    warnings: list[str] = Field(default_factory=list)


class LabelEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Literal[
        "true_positive",
        "false_positive",
        "benign_true_positive",
        "needs_review",
        "insufficient_evidence",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Literal["informational", "low", "medium", "high", "critical", "unknown"] = "unknown"
    rubric_scores: dict[str, int | float | str]
    rationale: str
    counter_evidence: list[str] = Field(default_factory=list)
    recommended_disposition: str


@dataclass
class SearchOptimizationResult:
    requested_query: str
    executed_query: str
    metadata: dict


class SubagentRunner:
    def __init__(self, llm: LLMProvider, subagents: dict[str, AgentConfig]):
        self.llm = llm
        self.subagents = subagents

    def optimize_search(self, event: dict, events_so_far: list[dict], request: dict) -> SearchOptimizationResult:
        payload = event.get("payload", {})
        requested_query = str(payload.get("query", ""))
        optimizer = self._find("search_optimizer", "before_search")
        if not optimizer or not requested_query:
            return self._original_search(requested_query, "optimizer_unavailable")

        prompt = {
            "task": "Optimize this Splunk SPL without changing investigation intent.",
            "requested_query": requested_query,
            "search_event": event,
            "request": request,
            "events_so_far": events_so_far,
            "rules": [
                "Preserve index, sourcetype, host, user, earliest, latest, and output intent unless impossible.",
                "Do not add destructive or side-effect commands.",
                "Do not use the Splunk map command.",
                "Return JSON only matching the requested schema.",
            ],
        }
        try:
            response = self.llm.complete(
                messages=[
                    Message(role="system", content=optimizer.system_prompt),
                    Message(role="user", content=json.dumps(prompt, default=str)),
                ],
                model=optimizer.model,
                temperature=optimizer.temperature,
                max_tokens=optimizer.max_tokens,
            )
            envelope = SearchOptimizationEnvelope.model_validate(json.loads(response.content))
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            logger.warning("Search optimizer failed; using original SPL: %s", exc)
            return self._original_search(requested_query, "optimizer_failed")

        if not self._safe_optimized_query(requested_query, envelope.optimized_query, envelope):
            return self._original_search(
                requested_query,
                "optimizer_rejected",
                {
                    "optimizer_agent": optimizer.id,
                    "proposed_query": envelope.optimized_query,
                    "changes": envelope.changes,
                    "warnings": envelope.warnings,
                    "semantic_equivalence": envelope.semantic_equivalence,
                    "risk": envelope.risk,
                },
            )

        return SearchOptimizationResult(
            requested_query=requested_query,
            executed_query=envelope.optimized_query,
            metadata={
                "applied": envelope.optimized_query != requested_query,
                "optimizer_agent": optimizer.id,
                "semantic_equivalence": envelope.semantic_equivalence,
                "risk": envelope.risk,
                "changes": envelope.changes,
                "warnings": envelope.warnings,
            },
        )

    def run_after_final(self, request: dict, events: list[dict], artifacts: list[dict], skip_ids: set[str]) -> list[dict]:
        generated: list[dict] = []
        for subagent in self._after_final_agents(skip_ids):
            if subagent.subagent_kind == "report":
                event = self._run_reporter(subagent, request, events, artifacts)
            elif subagent.subagent_kind == "labeler":
                event = self._run_labeler(subagent, request, events, artifacts)
            else:
                continue
            if event:
                generated.append(event)
        return generated

    def handoff(self, requested: str, task: str, events_so_far: list[dict]) -> tuple[str, str | None]:
        subagent = self._resolve_handoff(requested)
        if subagent is None:
            logger.warning("No sub-agent available for handoff %r.", requested)
            return (
                "No reporting sub-agent is available. Produce the final answer yourself "
                "as a `final` event. Remember to always respond with json.",
                None,
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
                "as a `final` event. Remember to always respond with json.",
                subagent.id,
            )

        return (
            f"The reporting sub-agent ({subagent.id}) returned the following report:\n\n"
            f"{report}\n\n"
            "Summarize this for the user using a `result_summary` event and then a `final` event. "
            "Remember to always respond with json.",
            subagent.id,
        )

    def _run_reporter(self, subagent: AgentConfig, request: dict, events: list[dict], artifacts: list[dict]) -> dict | None:
        prompt = {
            "task": "Produce a concise investigation report from the completed event stream.",
            "request": request,
            "events": events,
            "artifacts": _artifact_summaries(artifacts),
        }
        try:
            response = self.llm.complete(
                messages=[
                    Message(role="system", content=subagent.system_prompt),
                    Message(role="user", content=json.dumps(prompt, default=str)),
                ],
                model=subagent.model,
                temperature=subagent.temperature,
                max_tokens=subagent.max_tokens,
            )
        except Exception as exc:
            logger.exception("Reporting sub-agent %s failed.", subagent.id)
            return _failure_event(subagent, "Reporting failed", str(exc))

        return {
            "type": "result_summary",
            "title": "Report",
            "text": response.content,
            "payload": {"source": "subagent", "subagent_id": subagent.id, "kind": subagent.subagent_kind},
        }

    def _run_labeler(self, subagent: AgentConfig, request: dict, events: list[dict], artifacts: list[dict]) -> dict | None:
        prompt = {
            "task": "Classify the completed investigation using the configured rubric.",
            "response_contract": {
                "format": "json_object_only",
                "exact_keys": list(_LABEL_JSON_TEMPLATE.keys()),
                "template": _LABEL_JSON_TEMPLATE,
                "rules": [
                    "Return only one JSON object.",
                    "Do not wrap the JSON in Markdown or code fences.",
                    "Do not include explanatory text before or after the JSON object.",
                    "Use confidence as a number from 0.0 to 1.0.",
                ],
            },
            "request": request,
            "events": events,
            "artifacts": _artifact_summaries(artifacts),
            "allowed_labels": [
                "true_positive",
                "false_positive",
                "benign_true_positive",
                "needs_review",
                "insufficient_evidence",
            ],
        }
        messages = [
            Message(role="system", content=subagent.system_prompt),
            Message(role="user", content=json.dumps(prompt, default=str)),
        ]
        try:
            label = self._complete_label(subagent, messages)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            logger.warning("Labeling sub-agent %s failed validation; retrying once: %s", subagent.id, exc)
            retry_messages = [
                *messages,
                Message(role="assistant", content=getattr(exc, "doc", "") or ""),
                Message(role="user", content=_LABEL_CORRECTIVE_MESSAGE),
            ]
            try:
                label = self._complete_label(subagent, retry_messages)
            except (json.JSONDecodeError, ValidationError, ValueError, Exception) as retry_exc:
                logger.warning("Labeling sub-agent %s failed validation after retry: %s", subagent.id, retry_exc)
                return _failure_event(subagent, "Labeling failed", str(retry_exc))
        except Exception as exc:
            logger.exception("Labeling sub-agent %s failed.", subagent.id)
            return _failure_event(subagent, "Labeling failed", str(exc))

        return {
            "type": "finding",
            "title": f"Investigation label: {label.label.replace('_', ' ')}",
            "text": label.rationale,
            "payload": {
                "source": "subagent",
                "subagent_id": subagent.id,
                "kind": subagent.subagent_kind,
                **label.model_dump(),
            },
        }

    def _complete_label(self, subagent: AgentConfig, messages: list[Message]) -> LabelEnvelope:
        response = self.llm.complete(
            messages=messages,
            model=subagent.model,
            temperature=subagent.temperature,
            max_tokens=subagent.max_tokens,
        )
        return LabelEnvelope.model_validate(_json_object_from_text(response.content))

    def _find(self, kind: str, policy: str) -> AgentConfig | None:
        for subagent in self.subagents.values():
            if subagent.subagent_kind == kind and subagent.invoke_policy == policy:
                return subagent
        return None

    def _after_final_agents(self, skip_ids: set[str]) -> list[AgentConfig]:
        return [
            subagent for subagent in self.subagents.values()
            if subagent.invoke_policy == "after_final" and subagent.id not in skip_ids
        ]

    def _resolve_handoff(self, requested: str) -> AgentConfig | None:
        if requested and requested in self.subagents:
            return self.subagents[requested]
        handoff_agents = [
            subagent for subagent in self.subagents.values()
            if subagent.invoke_policy in ("on_handoff", "after_final")
        ]
        if len(handoff_agents) == 1:
            return handoff_agents[0]
        return None

    def _original_search(self, query: str, reason: str, extra: dict | None = None) -> SearchOptimizationResult:
        metadata = {"applied": False, "reason": reason}
        if extra:
            metadata.update(extra)
        return SearchOptimizationResult(query, query, metadata)

    def _safe_optimized_query(
        self,
        requested_query: str,
        optimized_query: str,
        envelope: SearchOptimizationEnvelope,
    ) -> bool:
        if not optimized_query.strip() or _SPL_DANGEROUS_RE.search(optimized_query):
            return False
        if envelope.semantic_equivalence == "changed" or envelope.risk == "high":
            return False
        return _preserves_required_terms(requested_query, optimized_query)


def _events_to_markdown(events: list[dict]) -> str:
    parts = []
    for event in events:
        title = event.get("title", "")
        text = event.get("text", "")
        parts.append(f"**{title}**\n\n{text}" if title else text)
    return "\n\n".join(p for p in parts if p)


def _json_object_from_text(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("empty JSON response")

    candidate = text.strip()
    fence_match = _CODE_FENCE_RE.match(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        # Request/response sub-agents sometimes add a short preface despite a
        # strict prompt. Extract one balanced top-level object, then still let
        # json.loads and Pydantic enforce the actual contract.
        candidate = _extract_balanced_json_object(candidate)
        parsed = json.loads(candidate)

    if not isinstance(parsed, dict):
        raise ValueError(f"expected JSON object, got {type(parsed).__name__}")
    return parsed


def _extract_balanced_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        raise ValueError("response did not contain a JSON object")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    raise ValueError("response contained an incomplete JSON object")


def _artifact_summaries(artifacts: list[dict]) -> list[dict]:
    summaries = []
    for artifact in artifacts:
        summaries.append({
            "id": artifact.get("id"),
            "type": artifact.get("type"),
            "title": artifact.get("title"),
            "status": artifact.get("status"),
            "fields": artifact.get("fields", []),
            "row_count": len(artifact.get("rows", [])),
            "sid": artifact.get("sid"),
            "optimization": artifact.get("optimization"),
        })
    return summaries


def _failure_event(subagent: AgentConfig, title: str, error: str) -> dict | None:
    if subagent.failure_policy == "fail_run" or subagent.required:
        return {
            "type": "finding",
            "title": title,
            "text": error,
            "payload": {
                "source": "subagent",
                "subagent_id": subagent.id,
                "kind": subagent.subagent_kind,
                "error": error,
            },
        }
    return None


def _preserves_required_terms(requested_query: str, optimized_query: str) -> bool:
    for pattern in (r"\bindex\s*=\s*([^\s|]+)", r"\bsourcetype\s*=\s*([^\s|]+)", r"\bhost\s*=\s*([^\s|]+)"):
        for value in re.findall(pattern, requested_query, re.IGNORECASE):
            if not re.search(pattern.replace("([^\s|]+)", re.escape(value)), optimized_query, re.IGNORECASE):
                return False
    return True
