"""
workers/job_worker.py
---------------------
RQ worker entry points.  Each function is the task callable pushed onto the
Redis queue by queue_service.enqueue_job().

execute_job(job_id)
    • Loads the Job record from the database
    • Dispatches to the correct handler by job_type
    • On success  → marks the job as "success"
    • On failure  → calls mark_job_failed() which handles retry / dead-letter

handle_dead_letter(job_id)
    • Minimal handler for dead-letter queue entries
    • Logs the event via the audit service

Running the worker:
    rq worker kba_jobs --url redis://localhost:6379/0
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone

from app import create_app
from models.job import Job
from services.audit_service import record_event
from services.queue_service import mark_job_started, mark_job_success, mark_job_failed
from extensions import db

# --- Dispatch table: add handlers here as new job types are introduced ---

def _handle_issue_certificate(payload: dict) -> dict:
    """Example handler: issue a certificate from a queued payload."""
    from services.certificate_service import issue_certificate

    cert = issue_certificate(
        owner_name=payload["owner_name"],
        owner_email=payload["owner_email"],
        issued_by=payload.get("issued_by"),
        metadata=payload.get("metadata"),
    )
    return {"certificate_id": cert.id, "serial_number": cert.serial_number}


_HANDLERS: dict = {
    "issue_certificate": _handle_issue_certificate,
    # Register additional handlers here:
    # "send_email": _handle_send_email,
}


# --------------------------------------------------------------------------- #
# Worker entry points                                                           #
# --------------------------------------------------------------------------- #

def execute_job(job_id: str) -> None:
    """
    Main worker function.  Called by RQ when a job is dequeued.

    Creates a Flask application context so that database and service
    calls work correctly inside the worker process.
    """
    app = create_app()
    with app.app_context():
        job: Job | None = Job.query.get(job_id)
        if job is None:
            return  # nothing to do

        mark_job_started(job_id)

        handler = _HANDLERS.get(job.job_type)
        if handler is None:
            mark_job_failed(job_id, f"Unknown job_type: {job.job_type}")
            return

        try:
            result = handler(job.payload or {})
            mark_job_success(job_id, result)
            record_event(
                "job_success",
                resource="job",
                resource_id=job_id,
                detail={"job_type": job.job_type},
            )
        except Exception:  # noqa: BLE001
            err = traceback.format_exc()
            mark_job_failed(job_id, err)
            record_event(
                "job_failed",
                resource="job",
                resource_id=job_id,
                detail={"job_type": job.job_type, "error": err[-500:]},
            )


def handle_dead_letter(job_id: str) -> None:
    """
    Called when a job has been moved to the dead-letter queue after
    exhausting all retries.  Logs the event for operator review.
    """
    app = create_app()
    with app.app_context():
        job: Job | None = Job.query.get(job_id)
        if job is None:
            return
        record_event(
            "job_dead_letter",
            resource="job",
            resource_id=job_id,
            detail={
                "job_type": job.job_type,
                "retries": job.retries,
                "last_error": job.error[-500:] if job.error else None,
            },
        )
