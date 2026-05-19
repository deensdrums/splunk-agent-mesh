"""Sentinel Mesh FastAPI backend."""

import logging
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from .config import CORS_ORIGINS, LOG_LEVEL
from .settings_store import get_settings_store
from .security import is_safe_model_name, is_safe_url, redact_key
from .agents.orchestrator import Orchestrator

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sentinel Mesh", version="0.1.0")

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
    return {"status": "ok", "service": "sentinel-mesh"}


@app.get("/api/v1/settings")
def get_settings():
    store = get_settings_store()
    cfg = store.get_provider_settings()
    return {
        "provider": cfg.get("provider", "anthropic"),
        "base_url": cfg.get("base_url"),
        "model": cfg.get("model", "claude-sonnet-4-6"),
        "api_key_configured": store.api_key_configured(),
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
    except Exception as e:
        logger.error("Settings save failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save settings.")
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
    store.clear_api_key()
    return {"cleared": True}


@app.post("/api/v1/investigations/run")
def run_investigation(req: InvestigationRequest):
    if not req.description.strip() and not req.demo:
        raise HTTPException(status_code=400, detail="description is required.")

    store = get_settings_store()
    cfg = store.get_provider_settings()

    llm = None
    splunk = None

    if not req.demo:
        key = store.get_api_key()
        if key:
            llm = _build_provider(cfg.get("provider", "anthropic"), key, cfg.get("model", ""), cfg.get("base_url", ""))

        from .splunk_client import DemoSplunkClient
        splunk = DemoSplunkClient()

    orchestrator = Orchestrator(llm_provider=llm, splunk_client=splunk)
    result = orchestrator.run(req.model_dump())
    return result


@app.get("/api/v1/investigations/{investigation_id}")
def get_investigation(investigation_id: str):
    raise HTTPException(status_code=501, detail="Investigation history not yet implemented.")


# ---- Helpers ----

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
