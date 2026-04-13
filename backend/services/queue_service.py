"""
services/queue_service.py
--------------------------
Wraps RQ (Redis Queue) to provide:
  • enqueue_job(job_type, payload) — creates a Job record and pushes to Redis
  • retry logic          — jobs are requeued up to max_retries times
  • dead-letter logic    — exhausted jobs are moved to a dead-letter queue

The actual job execution is in workers/job_worker.py.  This service only
handles enqueuing and state management.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from rq import Queue
from extensions import db, init_redis
from models.job import Job
from config import get_config


def _get_queue(name: str | None = None) -> Queue:
    cfg = get_config()
    redis = init_redis()
    return Queue(name or cfg.RQ_QUEUE_NAME, connection=redis)


def enqueue_job(
    job_type: str,
    payload: dict | None = None,
    max_retries: int | None = None,
) -> Job:
    """
    Create a persistent Job record and push it onto the Redis queue.

    Returns the Job ORM instance.
    """
    cfg = get_config()
    job_id = str(uuid.uuid4())
    max_retries = max_retries if max_retries is not None else cfg.RQ_MAX_RETRIES

    job = Job(
        id=job_id,
        queue_name=cfg.RQ_QUEUE_NAME,
        job_type=job_type,
        payload=payload or {},
        status="queued",
        retries=0,
        max_retries=max_retries,
    )
    db.session.add(job)
    db.session.commit()

    queue = _get_queue()
    queue.enqueue(
        "workers.job_worker.execute_job",
        job_id,
        job_id=job_id,
    )
    return job


def mark_job_started(job_id: str) -> Job | None:
    job = Job.query.get(job_id)
    if job:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.session.commit()
    return job


def mark_job_success(job_id: str, result: dict | None = None) -> Job | None:
    job = Job.query.get(job_id)
    if job:
        job.status = "success"
        job.result = result or {}
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
    return job


def mark_job_failed(job_id: str, error: str) -> Job | None:
    """
    Increment retry counter.  If retries are exhausted, dead-letter the job.
    Otherwise, re-enqueue on the main queue.
    """
    cfg = get_config()
    job = Job.query.get(job_id)
    if not job:
        return None

    job.retries += 1
    job.error = error

    if job.retries >= job.max_retries:
        # Move to dead-letter queue
        job.status = "dead"
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        dl_queue = _get_queue(cfg.DEAD_LETTER_QUEUE_NAME)
        dl_queue.enqueue(
            "workers.job_worker.handle_dead_letter",
            job_id,
            job_id=f"dl-{job_id}",
        )
    else:
        job.status = "queued"
        db.session.commit()
        queue = _get_queue()
        queue.enqueue(
            "workers.job_worker.execute_job",
            job_id,
            job_id=job_id,
        )
    return job
