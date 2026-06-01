"""Splunk Agent Mesh FastAPI backend."""

import asyncio
import json
import logging
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from .config import CORS_ORIGINS, LOG_LEVEL, SPLUNK_HOST, SPLUNK_TOKEN
from .conf_reader import get_conf_reader
from .job_store import JOB_STORE
from .request_context import RequestContext, context_from_request
from .settings_store import get_settings_store
from .splunk_client import DemoSplunkClient, SplunkClient
from .security import is_safe_model_name, is_safe_url, redact_key
from .agents.orchestrator import Orchestrator

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="Splunk Agent Mesh", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Request / Response models ----

_ENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,63}$")
_TIME_RANGE_PATTERN = re.compile(r"^[A-Za-z0-9@\-+:/. ]{1,32}$")


class InvestigationRequest(BaseModel):
    description: str = Field(..., max_length=10_000)
    host: Optional[str] = Field(default=None, max_length=64)
    user: Optional[str] = Field(default=None, max_length=64)
    alert_name: Optional[str] = Field(default=None, max_length=200)
    time_range: Optional[str] = Field(default="-24h", max_length=32)
    demo: bool = False

    @field_validator("host", "user")
    @classmethod
    def validate_entity(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not _ENTITY_PATTERN.match(v):
            raise ValueError("must be alphanumeric with . _ - only")
        return v

    @field_validator("time_range")
    @classmethod
    def validate_time_range(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not _TIME_RANGE_PATTERN.match(v):
            raise ValueError("invalid time_range format")
        return v


class SaveSettingsRequest(BaseModel):
    provider: str
    base_url: Optional[str] = None
    model: str
    api_key: Optional[str] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in ("anthropic", "openrouter", "openai_compatible"):
            raise ValueError("Invalid provider")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not is_safe_model_name(v):
            raise ValueError("Invalid model name")
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not is_safe_url(v):
            raise ValueError("Invalid base URL")
        return v


# ---- Routes ----

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "splunk-agent-mesh"}


@app.get("/api/v1/settings")
def get_settings():
    store = get_settings_store()
    cfg = store.get_provider_settings()
    return {
        "provider": cfg.get("provider", "anthropic"),
        "base_url": cfg.get("base_url"),
        "model": cfg.get("model", "claude-sonnet-4-6"),
        "api_key_configured": store.api_key_configured(),
        "storage_backend": type(store).__name__,
    }


@app.post("/api/v1/settings")
def save_settings(req: SaveSettingsRequest):
    store = get_settings_store()
    try:
        store.save_provider_settings(req.provider, req.base_url, req.model)
        if req.api_key:
            store.store_api_key(req.api_key)
            logger.info("API key stored (redacted: %s).", redact_key(req.api_key))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RuntimeError as e:
        # Storage-backend errors (e.g. Splunk REST returned non-2xx). Surface
        # the underlying message so the user can act on it.
        logger.error("Settings save failed via %s: %s", type(store).__name__, e)
        raise HTTPException(status_code=502, detail=f"Storage backend error: {e}")
    except Exception as e:
        logger.exception("Settings save failed unexpectedly.")
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")
    return {"saved": True, "api_key_configured": store.api_key_configured()}


@app.post("/api/v1/settings/test")
def test_connection():
    store = get_settings_store()
    key = store.get_api_key()
    if not key:
        return {"success": False, "error": "No API key configured. Save settings first."}

    cfg = store.get_provider_settings()
    provider_name = cfg.get("provider", "anthropic")
    model = cfg.get("model", "")
    base_url = cfg.get("base_url", "")

    try:
        provider = _build_provider(provider_name, key, model, base_url)
        return provider.test_connection()
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/v1/settings/credentials")
def clear_credentials():
    store = get_settings_store()
    try:
        store.clear_api_key()
    except RuntimeError as e:
        logger.error("Clear credentials failed via %s: %s", type(store).__name__, e)
        raise HTTPException(status_code=502, detail=f"Storage backend error: {e}")
    return {"cleared": True}


@app.get("/api/v1/agents")
def list_agents():
    """Configured agents (id, display_name, description, order, enabled).

    No system prompts in the response — the frontend doesn't need them and
    they can be long.
    """
    orchestrator = Orchestrator(conf_reader=get_conf_reader())
    return {"agents": orchestrator.get_agent_descriptors()}


@app.post("/api/v1/investigations/run")
def run_investigation(req: InvestigationRequest, http_request: Request):
    if not req.description.strip() and not req.demo:
        raise HTTPException(status_code=400, detail="description is required.")

    context = context_from_request(http_request)
    orchestrator = _build_orchestrator(req.demo, context)
    result = orchestrator.run(req.model_dump())
    return result


@app.post("/api/v1/investigations/start")
def start_investigation(req: InvestigationRequest, http_request: Request):
    if not req.description.strip() and not req.demo:
        raise HTTPException(status_code=400, detail="description is required.")

    context = context_from_request(http_request)
    payload = req.model_dump()

    def runner(
        run_payload: dict,
        run_context: RequestContext,
        investigation_id: str,
        progress_callback,
    ) -> dict:
        orchestrator = _build_orchestrator(bool(run_payload.get("demo")), run_context)
        return orchestrator.run(
            run_payload,
            investigation_id=investigation_id,
            progress_callback=progress_callback,
        )

    job = JOB_STORE.create(payload, context, runner)
    return {
        "id": job["id"],
        "status": job["status"],
        "owner": job["owner"],
        "started_at": job["started_at"],
    }


@app.get("/api/v1/investigations/{investigation_id}/status")
def get_investigation_status(investigation_id: str, http_request: Request):
    context = context_from_request(http_request)
    status = JOB_STORE.status(investigation_id, username=context.username)
    if status is None:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return status


@app.post("/api/v1/investigations/{investigation_id}/cancel")
def cancel_investigation(investigation_id: str, http_request: Request):
    context = context_from_request(http_request)
    job = JOB_STORE.cancel(investigation_id, username=context.username)
    if job is None:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return {"id": investigation_id, "status": job["status"], "completed_at": job.get("completed_at")}


@app.get("/api/v1/investigations/{investigation_id}/stream")
async def stream_investigation(investigation_id: str):
    """SSE stream of investigation progress.

    Emits events as each agent completes. The investigation ID is the
    access credential — EventSource cannot send custom headers, so
    header-based auth is not possible here. Production path: signed
    stream token returned by POST /investigations/start.
    """
    return StreamingResponse(
        _stream_events(investigation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/investigations/{investigation_id}")
def get_investigation(investigation_id: str, http_request: Request):
    context = context_from_request(http_request)
    job = JOB_STORE.get(investigation_id, username=context.username)
    if job is None:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return job


async def _stream_events(investigation_id: str):
    seen_agent_iters: dict[str, int] = {}
    seen_artifact_revisions: dict[str, int] = {}
    order_sent = False
    polls_with_no_job = 0

    while True:
        job = JOB_STORE.get(investigation_id)

        if job is None:
            polls_with_no_job += 1
            if polls_with_no_job >= 10:
                yield _sse_event({"type": "error", "message": "Investigation not found"})
                return
            await asyncio.sleep(0.3)
            continue

        if not order_sent and job.get("agent_order"):
            order_sent = True
            yield _sse_event({"type": "agent_order", "agent_order": job["agent_order"]})

        for agent_id, output in job.get("agents", {}).items():
            current_iter = output.get("_iteration", 0)
            last_iter = seen_agent_iters.get(agent_id, -1)
            agent_artifacts = [a for a in job.get("artifacts", []) if a.get("agent_id") == agent_id]
            changed_artifacts = [
                a for a in agent_artifacts
                if a.get("_revision", 0) > seen_artifact_revisions.get(a.get("id"), -1)
            ]

            if current_iter > last_iter or changed_artifacts:
                seen_agent_iters[agent_id] = current_iter
                for artifact in changed_artifacts:
                    seen_artifact_revisions[artifact["id"]] = artifact.get("_revision", 0)
                is_final = output.get("status") not in ("running", "iterating")
                yield _sse_event({
                    "type": "agent_complete" if is_final else "agent_update",
                    "agent_id": agent_id,
                    "output": output,
                    "artifacts": changed_artifacts,
                })

        if job["status"] not in ("running", "pending"):
            yield _sse_event({
                "type": "investigation_complete",
                "status": job["status"],
                "completed_at": job.get("completed_at"),
            })
            return

        yield ": keepalive\n\n"
        await asyncio.sleep(0.3)


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


# ---- Helpers ----

def _build_orchestrator(is_demo: bool, context: RequestContext) -> Orchestrator:
    store = get_settings_store()
    cfg = store.get_provider_settings()

    llm = None
    if not is_demo:
        key = store.get_api_key()
        if key:
            llm = _build_provider(
                cfg.get("provider", "anthropic"),
                key,
                cfg.get("model", ""),
                cfg.get("base_url", ""),
            )

    return Orchestrator(
        conf_reader=get_conf_reader(),
        llm_provider=llm,
        context=context,
        splunk_client_factory=lambda: _build_splunk_client(is_demo, context),
    )


def _build_splunk_client(is_demo: bool, context: RequestContext) -> SplunkClient | None:
    if is_demo:
        return DemoSplunkClient()
    token = context.splunk_token or SPLUNK_TOKEN
    if not token:
        return None
    return SplunkClient(SPLUNK_HOST, token)

def _build_provider(provider: str, key: str, model: str, base_url: str):
    if provider == "anthropic":
        from .llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=key, model=model or "claude-sonnet-4-6")
    elif provider == "openrouter":
        from .llm.openrouter_provider import OpenRouterProvider
        return OpenRouterProvider(api_key=key, model=model or "anthropic/claude-sonnet-4-6")
    elif provider == "openai_compatible":
        from .llm.openai_compatible_provider import OpenAICompatibleProvider
        return OpenAICompatibleProvider(api_key=key, base_url=base_url or "https://api.openai.com/v1", model=model or "gpt-4o")
    raise ValueError(f"Unknown provider: {provider}")
