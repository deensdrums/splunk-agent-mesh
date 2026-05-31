"""Reads agents.conf — either via Splunk REST API or from a local file.

Splunk REST is the primary path when SPLUNK_TOKEN is set. The file reader is a
fallback for unit tests and dev environments without a running Splunkd.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from configparser import ConfigParser
from pathlib import Path

import httpx

from .agents.agent_config import AgentConfig

logger = logging.getLogger(__name__)


_STANZA_PREFIX = "agent:"


def _coerce_bool(value: object, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "yes", "on", "enabled"):
        return True
    if s in ("0", "false", "no", "off", "disabled"):
        return False
    return default


def _coerce_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_list(value: object) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _build_agent_config(stanza_id: str, merged: dict[str, str]) -> AgentConfig | None:
    if not stanza_id.startswith(_STANZA_PREFIX):
        return None
    agent_id = stanza_id[len(_STANZA_PREFIX):].strip()
    if not agent_id:
        return None
    system_prompt = merged.get("system_prompt", "").strip()
    if not system_prompt:
        logger.warning("Agent stanza %r has no system_prompt; skipping.", stanza_id)
        return None
    agent_mode = merged.get("agent_mode", "single_shot")
    if agent_mode not in ("single_shot", "agentic"):
        logger.warning("Agent %r has invalid agent_mode %r; defaulting to single_shot.", agent_id, agent_mode)
        agent_mode = "single_shot"

    agent_role = merged.get("agent_role", "primary")
    if agent_role not in ("primary", "subagent"):
        logger.warning("Agent %r has invalid agent_role %r; defaulting to primary.", agent_id, agent_role)
        agent_role = "primary"

    return AgentConfig(
        id=agent_id,
        display_name=merged.get("display_name", agent_id),
        description=merged.get("description", ""),
        system_prompt=system_prompt,
        model=merged.get("model", "claude-sonnet-4-6"),
        temperature=_coerce_float(merged.get("temperature"), 0.2),
        max_tokens=_coerce_int(merged.get("max_tokens"), 2048),
        order=_coerce_int(merged.get("order"), 100),
        enabled=_coerce_bool(merged.get("enabled"), True),
        output_format=merged.get("output_format", "markdown"),
        skills=_coerce_list(merged.get("skills")),
        depends_on=_coerce_list(merged.get("depends_on")),
        agent_mode=agent_mode,
        max_iterations=_coerce_int(merged.get("max_iterations"), 10),
        agent_role=agent_role,
    )


class ConfReader(ABC):
    @abstractmethod
    def get_agents(self) -> list[AgentConfig]:
        """Return enabled agents sorted by their `order` value."""


class FileConfReader(ConfReader):
    """Parses agents.conf from one or more on-disk paths.

    Later paths override earlier ones (default <- local).
    Splunk conf line continuation (trailing backslash) is collapsed before parsing.
    """

    _CONTINUATION_RE = re.compile(r"\\\s*\n[ \t]*")

    def __init__(self, paths: list[Path]):
        self.paths = paths

    def get_agents(self) -> list[AgentConfig]:
        parser = ConfigParser(strict=False, interpolation=None)
        for path in self.paths:
            if not path.exists():
                logger.debug("Conf path %s does not exist; skipping.", path)
                continue
            text = path.read_text()
            collapsed = self._CONTINUATION_RE.sub(" ", text)
            try:
                parser.read_string(collapsed, source=str(path))
            except Exception as exc:  # pragma: no cover - malformed conf
                logger.error("Failed to parse %s: %s", path, exc)

        defaults = dict(parser["default"]) if parser.has_section("default") else {}
        agents: list[AgentConfig] = []
        for section in parser.sections():
            if not section.startswith(_STANZA_PREFIX):
                continue
            merged = {**defaults, **dict(parser[section])}
            cfg = _build_agent_config(section, merged)
            if cfg and cfg.enabled:
                agents.append(cfg)
        agents.sort(key=lambda a: (a.order, a.id))
        return agents


class SplunkRestConfReader(ConfReader):
    """Reads agents.conf via Splunk REST API.

    Calls /servicesNS/nobody/<app>/configs/conf-agents and merges the [default]
    stanza into each agent stanza. Returns a flat list ordered by `order`.
    """

    def __init__(self, splunk_host: str, token: str, app: str, verify: bool = False):
        self.splunk_host = splunk_host.rstrip("/")
        self.token = token
        self.app = app
        self.verify = verify

    def get_agents(self) -> list[AgentConfig]:
        url = f"{self.splunk_host}/servicesNS/nobody/{self.app}/configs/conf-agents"
        params = {"output_mode": "json", "count": "0"}
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = httpx.get(url, params=params, headers=headers, verify=self.verify, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Failed to read agents.conf via REST: %s", exc)
            return []

        payload = response.json()
        entries = payload.get("entry", [])
        defaults: dict[str, str] = {}
        agent_sections: dict[str, dict[str, str]] = {}
        for entry in entries:
            name = entry.get("name", "")
            content = entry.get("content", {})
            stringified = {k: str(v) for k, v in content.items() if not k.startswith("eai:") and k != "disabled"}
            if name == "default":
                defaults = stringified
            elif name.startswith(_STANZA_PREFIX):
                agent_sections[name] = stringified

        agents: list[AgentConfig] = []
        for stanza, content in agent_sections.items():
            merged = {**defaults, **content}
            cfg = _build_agent_config(stanza, merged)
            if cfg and cfg.enabled:
                agents.append(cfg)
                logger.info("Loaded agent %s (skills=%r).", cfg.id, cfg.skills)
        agents.sort(key=lambda a: (a.order, a.id))
        return agents


def get_conf_reader() -> ConfReader:
    """Factory: Splunk REST if SPLUNK_TOKEN is configured, else file."""
    from .config import SPLUNK_HOST, SPLUNK_TOKEN, SPLUNK_APP_ID, AGENTS_CONF_PATHS

    if SPLUNK_TOKEN:
        logger.info("Using SplunkRestConfReader (host=%s app=%s).", SPLUNK_HOST, SPLUNK_APP_ID)
        return SplunkRestConfReader(SPLUNK_HOST, SPLUNK_TOKEN, SPLUNK_APP_ID)
    logger.info("SPLUNK_TOKEN not set; using FileConfReader fallback.")
    return FileConfReader(AGENTS_CONF_PATHS)
