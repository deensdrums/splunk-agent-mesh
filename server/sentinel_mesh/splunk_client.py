"""Splunk REST API client for running SPL searches.

In demo/MVP mode, returns synthetic event data instead of calling Splunk.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    spl: str
    events: list[dict] = field(default_factory=list)
    error: str | None = None


class SplunkClient:
    def __init__(self, host: str, token: str, verify_ssl: bool = False):
        self.host = host
        self.token = token
        self.verify_ssl = verify_ssl

    def run_search(self, spl: str, earliest: str = "-24h", latest: str = "now") -> SearchResult:
        """Run an SPL search and return events.

        Currently a stub. Replace with real Splunk SDK or REST calls.

        Real implementation:
          POST {host}/services/search/jobs  → get sid
          GET  {host}/services/search/jobs/{sid}/results  → get events
        """
        logger.info("SplunkClient.run_search (stub): %s", spl[:120])
        return SearchResult(spl=spl, events=[], error="Splunk client stub — no real connection configured.")


class DemoSplunkClient(SplunkClient):
    """Returns synthetic events for the demo scenario without Splunk connectivity."""

    def __init__(self):
        super().__init__(host="demo", token="demo")

    def run_search(self, spl: str, earliest: str = "-24h", latest: str = "now") -> SearchResult:
        from .demo.synthetic_events import get_demo_events_for_spl
        events = get_demo_events_for_spl(spl)
        logger.info("DemoSplunkClient returned %d events for query.", len(events))
        return SearchResult(spl=spl, events=events)
