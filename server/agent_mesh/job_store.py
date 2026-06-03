"""In-memory investigation job manager.

This is intentionally small and replaceable. It gives the UI a non-blocking job
API now, while leaving room for Splunk KV Store or another durable backend.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Callable

from .durable_investigations import DurableInvestigationError, investigation_record, repository_from_context
from .investigation_models import audit_event, now_iso

if TYPE_CHECKING:
    from .request_context import RequestContext
    from .durable_investigations import NullInvestigationRepository, SplunkKVInvestigationRepository

logger = logging.getLogger(__name__)


class InvestigationJobStore:
    def __init__(
        self,
        max_workers: int = 4,
        durable_repository_factory: Callable[
            ["RequestContext"], "SplunkKVInvestigationRepository | NullInvestigationRepository"
        ] | None = None,
    ):
        self._jobs: dict[str, dict] = {}
        self._requests: dict[str, dict] = {}
        self._contexts: dict[str, RequestContext] = {}
        self._durable_failures: dict[str, str] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="investigation")
        self._durable_repository_factory = durable_repository_factory

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
            "updated_at": started_at,
            "agent_order": [],
            "agents": {},
            "sections": [],
            "artifacts": [],
            "request": dict(request_payload),
            "audit": [
                audit_event("investigation_started", investigation_id, context.username, source=context.source)
            ],
            "error": None,
            "persistence_error": None,
        }
        with self._lock:
            self._jobs[investigation_id] = job
            self._requests[investigation_id] = dict(request_payload)
            self._contexts[investigation_id] = context
        self._checkpoint(investigation_id, "create")
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
                job["updated_at"] = job["completed_at"]
                job.setdefault("audit", []).append(
                    audit_event("investigation_cancelled", investigation_id, username or job["owner"])
                )
            snapshot = dict(job)
        self._checkpoint(investigation_id, "cancel")
        return snapshot

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
                current["updated_at"] = now_iso()
                current.setdefault("request", dict(request_payload))
            self._checkpoint(investigation_id, "complete")
        except Exception as exc:  # pragma: no cover - defensive job boundary
            logger.exception("Investigation job %s failed.", investigation_id)
            with self._lock:
                current = self._jobs.get(investigation_id)
                if current:
                    current["status"] = "error"
                    current["completed_at"] = now_iso()
                    current["updated_at"] = current["completed_at"]
                    current["error"] = str(exc)
                    current.setdefault("audit", []).append(
                        audit_event("investigation_failed", investigation_id, context.username, "error", error=str(exc))
                    )
            self._checkpoint(investigation_id, "failure")

    def apply_update(self, investigation_id: str, update: dict) -> None:
        with self._lock:
            current = self._jobs.get(investigation_id)
            if not current or current.get("status") == "cancelled":
                return
            if "agent_order" in update:
                current["agent_order"] = update["agent_order"]
            if "agents" in update:
                current.setdefault("agents", {}).update(update["agents"])
            for key in ("sections", "audit"):
                if key in update:
                    current.setdefault(key, []).extend(update[key])
            if "artifacts" in update:
                artifacts = current.setdefault("artifacts", [])
                by_id = {artifact.get("id"): index for index, artifact in enumerate(artifacts)}
                for artifact in update["artifacts"]:
                    artifact_id = artifact.get("id")
                    if artifact_id in by_id:
                        artifacts[by_id[artifact_id]] = artifact
                    else:
                        by_id[artifact_id] = len(artifacts)
                        artifacts.append(artifact)
            current["updated_at"] = now_iso()
        self._checkpoint(investigation_id, "update")

    def _checkpoint(self, investigation_id: str, reason: str) -> None:
        if not self._durable_repository_factory:
            return
        with self._lock:
            current = self._jobs.get(investigation_id)
            context = self._contexts.get(investigation_id)
            request_payload = self._requests.get(investigation_id)
            if not current or not context:
                return
            snapshot = dict(current)
        try:
            repository = self._durable_repository_factory(context)
            record = investigation_record(snapshot, request_payload, context)
            repository.upsert(record)
            with self._lock:
                if investigation_id in self._jobs:
                    self._jobs[investigation_id]["_durable_revision"] = record["record_revision"]
                    self._jobs[investigation_id]["persistence_error"] = None
                self._durable_failures.pop(investigation_id, None)
        except DurableInvestigationError as exc:
            logger.warning("Durable checkpoint failed for %s (%s): %s", investigation_id, reason, exc)
            with self._lock:
                self._durable_failures[investigation_id] = str(exc)
                if investigation_id in self._jobs:
                    self._jobs[investigation_id]["persistence_error"] = str(exc)
        except Exception as exc:  # pragma: no cover - defensive persistence boundary
            logger.exception("Unexpected durable checkpoint failure for %s (%s).", investigation_id, reason)
            with self._lock:
                self._durable_failures[investigation_id] = str(exc)
                if investigation_id in self._jobs:
                    self._jobs[investigation_id]["persistence_error"] = str(exc)


JOB_STORE = InvestigationJobStore(durable_repository_factory=repository_from_context)
