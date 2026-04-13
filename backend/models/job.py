"""
models/job.py
-------------
Persistent record of every background job submitted to the Redis queue.
This table acts as the source of truth for job state, retry counts, and
dead-letter bookkeeping independent of Redis.

Columns
-------
id          UUID job identifier (also used as RQ job id)
queue_name  RQ queue the job was placed on
job_type    logical name, e.g. "issue_certificate", "send_email"
payload     JSON input data for the job
status      queued | running | success | failed | dead
retries     how many times execution has been attempted
max_retries maximum allowed retries before dead-lettering
result      JSON output on success
error       error traceback on failure
enqueued_at when the job was created
started_at  when the worker picked it up
finished_at when the job completed (success or dead)
"""

import uuid
from datetime import datetime, timezone
from extensions import db


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    queue_name = db.Column(db.String(80), nullable=False, index=True)
    job_type = db.Column(db.String(80), nullable=False, index=True)
    payload = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="queued", index=True)
    retries = db.Column(db.Integer, default=0, nullable=False)
    max_retries = db.Column(db.Integer, default=3, nullable=False)
    result = db.Column(db.JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
    enqueued_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "queue_name": self.queue_name,
            "job_type": self.job_type,
            "status": self.status,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "enqueued_at": self.enqueued_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    def __repr__(self) -> str:
        return f"<Job {self.job_type} [{self.status}] retries={self.retries}>"
