"""SPL extraction, execution, and artifact normalization."""

from __future__ import annotations

import re
import uuid
from typing import Callable

from ..investigation_models import now_iso
from ..splunk_client import SearchResult, SplunkClient

_SPL_BLOCK_RE = re.compile(
    r"```(?:spl|splunk)(?:_([a-z]+))?\s*\n(.*?)```", re.IGNORECASE | re.DOTALL
)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,4}\s+(.+?)\s*$", re.MULTILINE)

_SPL_INDICATORS = re.compile(
    r"\b(index\s*=|stats\s|table\s|where\s|eval\s|search\s|sourcetype\s*=|timechart\s)", re.IGNORECASE
)

_VIZ_HINT_MAP: dict[str, str] = {
    "column": "timechart",
    "timechart": "timechart",
    "line": "line",
    "pie": "pie",
    "bar": "bar",
    "table": "table",
    "single": "single",
}


def extract_spl_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    for idx, match in enumerate(_SPL_BLOCK_RE.finditer(markdown), start=1):
        viz_suffix = match.group(1)
        spl = match.group(2).strip()
        if not spl:
            continue
        if not _SPL_INDICATORS.search(spl):
            continue
        prefix = markdown[: match.start()]
        headings = _HEADING_RE.findall(prefix)
        title = headings[-1] if headings else f"SPL search {idx}"
        viz_hint = _VIZ_HINT_MAP.get(viz_suffix.lower()) if viz_suffix else None
        blocks.append({"title": title, "spl": spl, "viz_hint": viz_hint})
    return blocks


def infer_visualization(
    spl: str, fields: list[str], rows: list[dict], preferred_view: str | None = None, viz_hint: str | None = None
) -> dict:
    allowed = {"table", "timechart", "bar", "single", "line", "pie"}

    if viz_hint and viz_hint in allowed:
        return {"kind": viz_hint, "reason": "Agent-specified visualization hint."}

    lower_spl = spl.lower()
    if preferred_view in allowed:
        preferred = preferred_view
    else:
        preferred = None

    if "timechart" in lower_spl:
        return {"kind": "timechart", "reason": "SPL uses timechart."}
    if "_time" in fields and _numeric_field_count(fields, rows) > 0:
        return {"kind": "timechart", "reason": "Results include _time and numeric series."}
    if len(rows) == 1 and _numeric_field_count(fields, rows) == 1:
        return {"kind": "single", "reason": "Results contain one numeric metric."}
    if _numeric_field_count(fields, rows) > 0 and len(fields) >= 2:
        return {"kind": "bar", "reason": "Results contain categorical fields and numeric measures."}
    if preferred:
        return {"kind": preferred, "reason": "Preferred view accepted as a fallback."}
    return {"kind": "table", "reason": "Table is the safe default for these results."}


def run_splunk_search_artifact(
    agent_id: str,
    title: str,
    spl: str,
    earliest: str,
    latest: str,
    client_factory: Callable[[], SplunkClient | None],
    preferred_view: str | None = None,
    viz_hint: str | None = None,
    timeout_seconds: float | None = None,
) -> dict:
    artifact_id = f"artifact-{uuid.uuid4().hex[:12]}"
    started_at = now_iso()
    client = client_factory()
    if client is None:
        return _artifact(
            artifact_id,
            agent_id,
            title,
            spl,
            earliest,
            latest,
            SearchResult(spl=spl, status="error", error="No Splunk token available for this investigation."),
            started_at,
            preferred_view,
            viz_hint,
        )
    kwargs: dict = {"earliest": earliest, "latest": latest}
    if timeout_seconds is not None:
        kwargs["timeout_seconds"] = timeout_seconds
    result = client.run_search(spl, **kwargs)
    return _artifact(artifact_id, agent_id, title, spl, earliest, latest, result, started_at, preferred_view, viz_hint)


def _artifact(
    artifact_id: str,
    agent_id: str,
    title: str,
    spl: str,
    earliest: str,
    latest: str,
    result: SearchResult,
    started_at: str,
    preferred_view: str | None,
    viz_hint: str | None = None,
) -> dict:
    rows = result.events
    fields = result.fields
    return {
        "id": artifact_id,
        "type": "splunk_search",
        "agent_id": agent_id,
        "title": title,
        "spl": spl,
        "earliest": earliest,
        "latest": latest,
        "sid": result.sid,
        "status": result.status,
        "fields": fields,
        "rows": rows,
        "messages": result.messages,
        "error": result.error,
        "started_at": started_at,
        "completed_at": now_iso() if result.status in ("done", "error") else None,
        "visualization": infer_visualization(spl, fields, rows, preferred_view, viz_hint),
    }


def _numeric_field_count(fields: list[str], rows: list[dict]) -> int:
    count = 0
    for field in fields:
        if field == "_time":
            continue
        values = [row.get(field) for row in rows if row.get(field) not in (None, "")]
        if values and all(_is_number(v) for v in values[:10]):
            count += 1
    return count


def _is_number(value: object) -> bool:
    try:
        float(str(value).replace(",", ""))
        return True
    except (TypeError, ValueError):
        return False

