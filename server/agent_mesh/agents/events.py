"""Shared structured-event schema for the threat hunter's response contract.

The threat hunter (spl_hunter) must respond with a single JSON object of the
shape ``{"events": [ {type,title,text,payload}, ... ]}``. This module is the
single boundary where that raw model text is parsed and validated, so neither
the orchestration loop nor the UI ever has to fix malformed model output.

Validation is intentionally close to the LLM boundary (per the architecture):
the harness calls :func:`parse_and_validate`; on any failure it feeds
:data:`CORRECTIVE_MESSAGE` back to the model and retries.

Pydantic is already a project dependency (FastAPI), so we lean on it rather
than adding a JSON-schema library or hand-rolling a validator.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger(__name__)

# Matches a response that is entirely one Markdown code fence, e.g.
#   ```json\n{ ... }\n```   or   ```\n{ ... }\n```
# Models (Claude and GPT alike) wrap JSON in a fence even when told not to, so
# we tolerate exactly this on the transport layer while keeping the schema
# strict. Bare JSON does not match (no leading ```), so it is never touched.
_CODE_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    match = _CODE_FENCE_RE.match(text)
    return match.group(1).strip() if match else text

# The corrective message routed back to the model whenever its output is not
# valid JSON matching the contract. Kept as a constant so the harness and tests
# agree on the exact string.
CORRECTIVE_MESSAGE = "Remember to always respond with json."

EVENT_TYPES = (
    "narration",
    "splunk_search",
    "result_summary",
    "finding",
    "handoff",
    "final",
)

# Event types that describe an external action the harness must execute. The
# harness runs at most one of these per turn (and expects it to be the last
# event in the array).
ACTION_EVENT_TYPES = frozenset({"splunk_search", "handoff"})

# Visualization hints the agent may put in a splunk_search payload's ``type``
# field. These map onto the visualization "kind" the artifact renderer already
# understands. "column" is an alias for "timechart" (both render via the
# @splunk/visualizations Column component) — preserved from the prior behavior.
VIZ_HINT_MAP: dict[str, str] = {
    "column": "timechart",
    "timechart": "timechart",
    "line": "line",
    "pie": "pie",
    "bar": "bar",
    "table": "table",
    "single": "single",
}


class AgentEvent(BaseModel):
    """One structured event emitted by the threat hunter.

    ``payload`` must be an object (never an array or scalar); use ``{}`` when
    there is nothing to attach. ``extra="forbid"`` rejects stray top-level keys
    so we fail closed on drifting output.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "narration",
        "splunk_search",
        "result_summary",
        "finding",
        "handoff",
        "final",
    ]
    title: str
    text: str
    payload: dict


class EventsEnvelope(BaseModel):
    """Top-level contract: an object with a non-empty ``events`` array.

    A wrapping object (rather than a bare array) is used so the contract can
    grow additional top-level fields later without breaking the schema.
    """

    model_config = ConfigDict(extra="forbid")

    events: list[AgentEvent]


def parse_and_validate(raw_text: str) -> tuple[list[dict] | None, str | None]:
    """Parse raw model text into a list of validated event dicts.

    Returns ``(events, None)`` on success or ``(None, CORRECTIVE_MESSAGE)`` on
    any JSON or schema failure. Events are returned as plain dicts so the rest
    of the pipeline keeps working with JSON-serializable structures.
    """
    if not raw_text or not raw_text.strip():
        logger.warning("Threat hunter response rejected: empty response.")
        return None, CORRECTIVE_MESSAGE

    # Strict first (fast path for well-behaved bare JSON), then one tolerant
    # retry that unwraps a surrounding Markdown code fence.
    candidate = _strip_code_fence(raw_text.strip())
    try:
        data = json.loads(candidate)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Threat hunter response rejected: not valid JSON (%s).", exc)
        return None, CORRECTIVE_MESSAGE

    if not isinstance(data, dict):
        logger.warning(
            "Threat hunter response rejected: top-level JSON is %s, expected an object.",
            type(data).__name__,
        )
        return None, CORRECTIVE_MESSAGE

    try:
        envelope = EventsEnvelope.model_validate(data)
    except ValidationError as exc:
        logger.warning("Threat hunter response rejected: schema validation failed: %s", exc)
        return None, CORRECTIVE_MESSAGE

    if not envelope.events:
        logger.warning("Threat hunter response rejected: empty events array.")
        return None, CORRECTIVE_MESSAGE

    return [event.model_dump() for event in envelope.events], None
