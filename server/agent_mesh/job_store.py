"""In-memory investigation job manager.

This is intentionally small and replaceable. It gives the UI a non-blocking job
API now, while leaving room for Splunk KV Store or another durable backend.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .investigation_models import audit_event, now_iso
from .request_context import RequestContext

logger = logging.getLogger(__name__)


class InvestigationJobStore:
    def __init__(self, max_workers: int = 4):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="investigation")

    def create(
        self,
        request_payload: dict,
        context: RequestContext,
        runner: Callable[[dict, RequestContext, str, Callable[[dict], None]], dict],
    ) -> dict:
        investigation_id = f"inv-{uuid.uuid4().hex[:12]}"
        started_at = now_iso()
        job = {
            "id": investigation_id,
            "owner": context.username,
            "status": "running",
            "started_at": started_at,
            "completed_at": None,
            "agent_order": [],
            "agents": {},
            "sections": [],
            "artifacts": [],
            "audit": [
                audit_event("investigation_started", investigation_id, context.username, source=context.source)
            ],
            "error": None,
        }
        with self._lock:
            self._jobs[investigation_id] = job
        self._executor.submit(self._run, investigation_id, request_payload, context, runner)
        return job

    def get(self, investigation_id: str, username: str | None = None) -> dict | None:
        with self._lock:
            job = self._jobs.get(investigation_id)
            if not job:
                return None
            if username and job.get("owner") != username:
                return None
            return dict(job)

    def status(self, investigation_id: str, username: str | None = None) -> dict | None:
        job = self.get(investigation_id, username)
        if not job:
            return None
        return {
            "id": job["id"],
            "owner": job["owner"],
            "status": job["status"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
            "agent_order": job.get("agent_order", []),
            "agents": {
                agent_id: {
                    "agent_id": output.get("agent_id"),
                    "display_name": output.get("display_name"),
                    "status": output.get("status"),
                    "started_at": output.get("started_at"),
                    "completed_at": output.get("completed_at"),
                    "error": output.get("error"),
                }
                for agent_id, output in job.get("agents", {}).items()
            },
            "artifact_count": len(job.get("artifacts", [])),
            "error": job.get("error"),
        }

    def cancel(self, investigation_id: str, username: str | None = None) -> dict | None:
        with self._lock:
            job = self._jobs.get(investigation_id)
            if not job:
                return None
            if username and job.get("owner") != username:
                return None
            if job["status"] == "running":
                job["status"] = "cancelled"
                job["completed_at"] = now_iso()
                job.setdefault("audit", []).append(
                    audit_event("investigation_cancelled", investigation_id, username or job["owner"])
                )
            return dict(job)

    def _run(
        self,
        investigation_id: str,
        request_payload: dict,
        context: RequestContext,
        runner: Callable[[dict, RequestContext, str], dict],
    ) -> None:
        try:
            result = runner(
                request_payload,
                context,
                investigation_id,
                lambda update: self.apply_update(investigation_id, update),
            )
            with self._lock:
                current = self._jobs.get(investigation_id)
                if not current or current.get("status") == "cancelled":
                    return
                current.update(result)
                current["owner"] = context.username
        except Exception as exc:  # pragma: no cover - defensive job boundary
            logger.exception("Investigation job %s failed.", investigation_id)
            with self._lock:
                current = self._jobs.get(investigation_id)
                if current:
                    current["status"] = "error"
                    current["completed_at"] = now_iso()
                    current["error"] = str(exc)
                    current.setdefault("audit", []).append(
                        audit_event("investigation_failed", investigation_id, context.username, "error", error=str(exc))
                    )

    def apply_update(self, investigation_id: str, update: dict) -> None:
        with self._lock:
            current = self._jobs.get(investigation_id)
            if not current or current.get("status") == "cancelled":
                return
            if "agent_order" in update:
                current["agent_order"] = update["agent_order"]
            if "agents" in update:
                current.setdefault("agents", {}).update(update["agents"])
            for key in ("sections", "artifacts", "audit"):
                if key in update:
                    current.setdefault(key, []).extend(update[key])


JOB_STORE = InvestigationJobStore()
