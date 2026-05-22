"""SPL extraction, execution, and artifact normalization."""

from __future__ import annotations

import re
import uuid
from typing import Callable

from ..investigation_models import now_iso
from ..splunk_client import SearchResult, SplunkClient

_SPL_BLOCK_RE = re.compile(r"```spl\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,4}\s+(.+?)\s*$", re.MULTILINE)


def extract_spl_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    for idx, match in enumerate(_SPL_BLOCK_RE.finditer(markdown), start=1):
        spl = match.group(1).strip()
        prefix = markdown[: match.start()]
        headings = _HEADING_RE.findall(prefix)
        title = headings[-1] if headings else f"SPL search {idx}"
        blocks.append({"title": title, "spl": spl})
    return blocks


def infer_visualization(spl: str, fields: list[str], rows: list[dict], preferred_view: str | None = None) -> dict:
    allowed = {"table", "timechart", "bar", "single"}
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
        )
    result = client.run_search(spl, earliest=earliest, latest=latest)
    return _artifact(artifact_id, agent_id, title, spl, earliest, latest, result, started_at, preferred_view)


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
        "visualization": infer_visualization(spl, fields, rows, preferred_view),
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

