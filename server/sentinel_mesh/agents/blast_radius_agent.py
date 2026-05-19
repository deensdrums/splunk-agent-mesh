"""Blast Radius Agent — identifies other affected systems."""

import logging

logger = logging.getLogger(__name__)


class BlastRadiusAgent:
    def __init__(self, llm=None, splunk_client=None):
        self.llm = llm
        self.splunk = splunk_client

    def run(self, ctx: dict) -> dict:
        events = ctx.get("events", [])
        entities = ctx.get("entities", {})
        known_hosts = set(entities.get("hosts", []))
        known_users = set(entities.get("users", []))

        additional_hosts: set[str] = set()
        additional_users: set[str] = set()

        for event in events:
            h = event.get("dest_host") or event.get("host")
            u = event.get("user")
            if h and h not in known_hosts:
                additional_hosts.add(h)
            if u and u not in known_users:
                additional_users.add(u)

        summary = "No additional systems identified." if not additional_hosts else (
            f"Lateral movement indicators found involving {', '.join(additional_hosts)}."
        )

        updated_entities = dict(entities)
        updated_entities["hosts"] = list(known_hosts | additional_hosts)
        updated_entities["users"] = list(known_users | additional_users)

        logger.info("BlastRadiusAgent: +%d hosts, +%d users.", len(additional_hosts), len(additional_users))
        return {
            "entities": updated_entities,
            "blast_radius_summary": summary,
            "additional_hosts": list(additional_hosts),
            "additional_users": list(additional_users),
        }
