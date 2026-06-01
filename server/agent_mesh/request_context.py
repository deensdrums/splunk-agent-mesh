"""Authenticated request context passed into orchestration and tools."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class RequestContext:
    username: str
    splunk_token: str | None = None
    splunk_auth_scheme: str = "Splunk"
    request_id: str | None = None
    source: str = "direct"


def context_from_request(request: Request) -> RequestContext:
    """Build context from headers supplied by the Splunk REST bridge.

    The intended production path is that Splunk REST authenticates the caller
    and forwards these headers server-to-server. Direct local calls fall back to
    a dev user and may use Authorization: Bearer for convenience.
    """
    auth = request.headers.get("authorization", "")
    bearer = auth.removeprefix("Bearer ").strip() if auth.lower().startswith("bearer ") else None
    session_key = request.headers.get("x-splunk-token")
    return RequestContext(
        username=request.headers.get("x-splunk-user", "dev-user"),
        splunk_token=session_key or bearer or None,
        splunk_auth_scheme="Splunk" if session_key else "Bearer",
        request_id=request.headers.get("x-request-id"),
        source=request.headers.get("x-agent-mesh-source", "direct"),
    )
