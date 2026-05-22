"""Splunk REST API client for running SPL searches.

In demo/MVP mode, returns synthetic event data instead of calling Splunk.
"""

import logging
from dataclasses import dataclass, field
from time import monotonic, sleep

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    spl: str
    sid: str | None = None
    status: str = "pending"
    fields: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    error: str | None = None


class SplunkClient:
    def __init__(self, host: str, token: str, verify_ssl: bool = False):
        self.host = host
        self.token = token
        self.verify_ssl = verify_ssl

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _url(self, path: str) -> str:
        return f"{self.host.rstrip('/')}{path}"

    def run_search(
        self,
        spl: str,
        earliest: str = "-24h",
        latest: str = "now",
        timeout_seconds: float = 8.0,
        max_rows: int = 100,
    ) -> SearchResult:
        """Create a Splunk search job, poll briefly, and return normalized rows."""
        search = spl if spl.strip().lower().startswith("search ") else f"search {spl}"
        try:
            create = httpx.post(
                self._url("/services/search/jobs"),
                data={
                    "search": search,
                    "earliest_time": earliest,
                    "latest_time": latest,
                    "output_mode": "json",
                },
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10.0,
            )
            create.raise_for_status()
            sid = create.json().get("sid")
            if not sid:
                return SearchResult(spl=spl, status="error", error="Splunk did not return a search id.")

            deadline = monotonic() + timeout_seconds
            while monotonic() < deadline:
                job = httpx.get(
                    self._url(f"/services/search/jobs/{sid}"),
                    params={"output_mode": "json"},
                    headers=self._headers(),
                    verify=self.verify_ssl,
                    timeout=10.0,
                )
                job.raise_for_status()
                content = (job.json().get("entry") or [{}])[0].get("content", {})
                if content.get("isDone"):
                    return self.get_results(sid, spl, max_rows)
                sleep(0.5)
            return SearchResult(spl=spl, sid=sid, status="running")
        except httpx.HTTPError as exc:
            logger.exception("Splunk search failed.")
            return SearchResult(spl=spl, status="error", error=str(exc))

    def get_results(self, sid: str, spl: str, max_rows: int = 100) -> SearchResult:
        try:
            resp = httpx.get(
                self._url(f"/services/search/jobs/{sid}/results"),
                params={"output_mode": "json", "count": str(max_rows)},
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=20.0,
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("results", [])
            fields = [f.get("name") for f in payload.get("fields", []) if f.get("name")]
            if not fields and rows:
                seen: list[str] = []
                for row in rows:
                    for key in row.keys():
                        if key not in seen:
                            seen.append(key)
                fields = seen
            messages = [
                f"{m.get('type', 'INFO')}: {m.get('text', '')}".strip()
                for m in payload.get("messages", [])
            ]
            return SearchResult(spl=spl, sid=sid, status="done", fields=fields, events=rows, messages=messages)
        except httpx.HTTPError as exc:
            logger.exception("Splunk results fetch failed.")
            return SearchResult(spl=spl, sid=sid, status="error", error=str(exc))

    def cancel_search(self, sid: str) -> bool:
        try:
            resp = httpx.post(
                self._url(f"/services/search/jobs/{sid}/control"),
                data={"action": "cancel", "output_mode": "json"},
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10.0,
            )
            return resp.status_code < 400
        except httpx.HTTPError:
            logger.exception("Splunk search cancel failed.")
            return False


class DemoSplunkClient(SplunkClient):
    """Returns synthetic events for the demo scenario without Splunk connectivity."""

    def __init__(self):
        super().__init__(host="demo", token="demo")

    def run_search(self, spl: str, earliest: str = "-24h", latest: str = "now") -> SearchResult:
        from .demo.synthetic_events import get_demo_events_for_spl
        events = get_demo_events_for_spl(spl)
        logger.info("DemoSplunkClient returned %d events for query.", len(events))
        fields: list[str] = []
        for row in events:
            for key in row.keys():
                if key not in fields:
                    fields.append(key)
        return SearchResult(spl=spl, sid="demo", status="done", fields=fields, events=events)
