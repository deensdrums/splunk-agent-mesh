"""Splunk REST API client for running SPL searches.

In demo/MVP mode, returns synthetic event data instead of calling Splunk.
"""

import logging
from dataclasses import dataclass, field
from time import monotonic, sleep
from typing import Callable

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
    def __init__(self, host: str, token: str, verify_ssl: bool = False, auth_scheme: str = "Bearer"):
        self.host = host
        self.token = token
        self.verify_ssl = verify_ssl
        self.auth_scheme = auth_scheme

    def _headers(self) -> dict:
        return {"Authorization": f"{self.auth_scheme} {self.token}"}

    def _url(self, path: str) -> str:
        return f"{self.host.rstrip('/')}{path}"

    def run_search(
        self,
        spl: str,
        earliest: str = "-24h",
        latest: str = "now",
        timeout_seconds: float = 8.0,
        max_rows: int = 100,
        on_update: Callable[[SearchResult], None] | None = None,
    ) -> SearchResult:
        """Create a Splunk search job and stream preview rows while polling."""
        dispatched = self.dispatch_search(spl, earliest, latest)
        if dispatched.status == "error" or not dispatched.sid:
            return dispatched
        if on_update:
            on_update(dispatched)

        deadline = monotonic() + timeout_seconds
        while monotonic() < deadline:
            status = self.get_search_status(dispatched.sid, spl)
            if status.status == "error":
                if on_update:
                    on_update(status)
                return status
            if status.status == "done":
                result = self.get_results(dispatched.sid, spl, max_rows)
                if on_update:
                    on_update(result)
                return result

            sleep(0.5)
        return dispatched

    def dispatch_search(self, spl: str, earliest: str = "-24h", latest: str = "now") -> SearchResult:
        """Create a Splunk search job with preview generation enabled."""
        search = spl if spl.strip().lower().startswith("search ") else f"search {spl}"
        try:
            create = httpx.post(
                self._url("/services/search/jobs"),
                data={
                    "search": search,
                    "earliest_time": earliest,
                    "latest_time": latest,
                    "status_buckets": "300",
                    "preview": "1",
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
            return SearchResult(spl=spl, sid=sid, status="running")
        except httpx.HTTPError as exc:
            logger.exception("Splunk search failed.")
            return SearchResult(spl=spl, status="error", error=str(exc))

    def get_search_status(self, sid: str, spl: str) -> SearchResult:
        try:
            job = httpx.get(
                self._url(f"/services/search/jobs/{sid}"),
                params={"output_mode": "json"},
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10.0,
            )
            job.raise_for_status()
            content = (job.json().get("entry") or [{}])[0].get("content", {})
            dispatch_state = content.get("dispatchState")
            if content.get("isDone") or dispatch_state == "DONE":
                return SearchResult(spl=spl, sid=sid, status="done")
            if dispatch_state in {"FAILED", "INTERNAL_CANCEL", "USER_CANCEL", "BAD_INPUT_CANCEL", "QUIT"}:
                return SearchResult(spl=spl, sid=sid, status="error", error=f"Splunk search ended: {dispatch_state}")
            return SearchResult(spl=spl, sid=sid, status="running")
        except httpx.HTTPError as exc:
            logger.exception("Splunk search status fetch failed.")
            return SearchResult(spl=spl, sid=sid, status="error", error=str(exc))

    def get_preview_results(self, sid: str, spl: str, max_rows: int = 100) -> SearchResult:
        """Return transformed preview rows for an in-flight search."""
        return self._get_results(
            f"/services/search/v2/jobs/{sid}/results_preview", sid, spl, "running", max_rows, tolerate_errors=True,
        )

    def get_results(self, sid: str, spl: str, max_rows: int = 100) -> SearchResult:
        return self._get_results(f"/services/search/v2/jobs/{sid}/results", sid, spl, "done", max_rows)

    def _get_results(
        self, path: str, sid: str, spl: str, status: str, max_rows: int, tolerate_errors: bool = False,
    ) -> SearchResult:
        try:
            resp = httpx.get(
                self._url(path),
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
            return SearchResult(spl=spl, sid=sid, status=status, fields=fields, events=rows, messages=messages)
        except httpx.HTTPError as exc:
            logger.exception("Splunk results fetch failed.")
            if tolerate_errors:
                return SearchResult(spl=spl, sid=sid, status="running")
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

    def get_authenticated_username(self) -> str | None:
        """Return the Splunk username represented by this credential."""
        try:
            response = httpx.get(
                self._url("/services/authentication/current-context"),
                params={"output_mode": "json"},
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10.0,
            )
            response.raise_for_status()
            content = (response.json().get("entry") or [{}])[0].get("content", {})
            return content.get("username")
        except httpx.HTTPError:
            logger.exception("Splunk session validation failed.")
            return None


class DemoSplunkClient(SplunkClient):
    """Returns synthetic events for the demo scenario without Splunk connectivity."""

    def __init__(self):
        super().__init__(host="demo", token="demo")

    def run_search(
        self,
        spl: str,
        earliest: str = "-24h",
        latest: str = "now",
        on_update: Callable[[SearchResult], None] | None = None,
        **_kwargs,
    ) -> SearchResult:
        from .demo.synthetic_events import get_demo_events_for_spl
        events = get_demo_events_for_spl(spl)
        logger.info("DemoSplunkClient returned %d events for query.", len(events))
        fields: list[str] = []
        for row in events:
            for key in row.keys():
                if key not in fields:
                    fields.append(key)
        result = SearchResult(spl=spl, sid="demo", status="done", fields=fields, events=events)
        if on_update:
            on_update(result)
        return result
