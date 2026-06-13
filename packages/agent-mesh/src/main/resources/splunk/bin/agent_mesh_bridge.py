"""Splunk-authenticated loopback proxy for the standalone agent-mesh service."""

from __future__ import annotations

import json
import logging
import os
import traceback
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from splunk.persistconn.application import PersistentServerConnectionApplication

logger = logging.getLogger("agent_mesh_bridge")

UVICORN_BASE_URL = os.environ.get("AGENT_MESH_UVICORN_URL", "http://127.0.0.1:8765").rstrip("/")


class AgentMeshBridge(PersistentServerConnectionApplication):
    """Forward allowlisted API calls with Splunk's authenticated session context."""

    def __init__(self, _command_line: str, _command_arg: str) -> None:
        super().__init__()

    def handle(self, in_string: str) -> dict:
        try:
            incoming = json.loads(in_string)
            session = incoming.get("session") or {}
            username = session.get("user")
            auth_token = session.get("authtoken")
            if not username or not auth_token:
                return self._response(401, {"detail": "Authenticated Splunk session required."})

            path = (incoming.get("path_info") or "").lstrip("/")
            if not path.startswith("api/v1/"):
                return self._response(404, {"detail": "Unknown agent-mesh bridge path."})

            query = incoming.get("query") or []
            if isinstance(query, dict):
                query_string = urlencode(query, doseq=True)
            elif isinstance(query, list):
                query_string = urlencode(query, doseq=True)
            else:
                query_string = ""
            url = f"{UVICORN_BASE_URL}/{path}"
            if query_string:
                url = f"{url}?{query_string}"

            payload = incoming.get("payload")
            if payload is None:
                body = None
            elif isinstance(payload, str):
                body = payload.encode("utf-8")
            else:
                body = json.dumps(payload).encode("utf-8")

            request = Request(
                url,
                data=body,
                method=(incoming.get("method") or "GET").upper(),
                headers={
                    "Content-Type": "application/json",
                    "X-Splunk-User": username,
                    "X-Splunk-Token": auth_token,
                    "X-Agent-Mesh-Source": "splunk-rest-bridge",
                },
            )
            with urlopen(request, timeout=130) as response:
                return self._response(response.status, self._decode(response.read()))
        except HTTPError as exc:
            return self._response(exc.code, self._decode(exc.read()))
        except URLError:
            return self._response(502, {"detail": "Agent Mesh backend is unavailable."})
        except Exception:
            logger.error("Bridge request failed: %s", traceback.format_exc())
            return self._response(500, {"detail": "Agent Mesh bridge request failed."})

    @staticmethod
    def _decode(body: bytes):
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"detail": "Agent Mesh backend returned an invalid response."}

    @staticmethod
    def _response(status: int, payload) -> dict:
        return {
            "status": status,
            "headers": {"Content-Type": "application/json"},
            "payload": payload,
        }
