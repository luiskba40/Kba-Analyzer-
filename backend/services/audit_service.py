"""
services/audit_service.py
--------------------------
Single-responsibility service for writing audit log entries.

Call record_event() from any route or service layer to persist an
immutable audit trail record without coupling the caller to the
AuditLog model directly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from extensions import db
from models.audit_log import AuditLog


def record_event(
    action: str,
    *,
    user_id: str | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Persist an audit log entry and return it.

    Parameters
    ----------
    action      : short verb describing what happened, e.g. "login"
    user_id     : UUID of the acting user (None for system events)
    resource    : resource type, e.g. "certificate"
    resource_id : UUID of the specific resource
    detail      : arbitrary JSON detail blob
    ip_address  : originating IP address string
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def get_recent_events(limit: int = 100) -> list[AuditLog]:
    """Return the most recent *limit* audit log entries."""
    return (
        AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    )
