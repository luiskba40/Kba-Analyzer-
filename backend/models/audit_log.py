"""
models/audit_log.py
-------------------
Immutable audit trail.  Every significant action performed by a user or
the system is persisted here for compliance and forensic purposes.

Columns
-------
id          UUID primary key
user_id     FK → users (nullable for system actions)
action      short verb, e.g. "login", "cert_issued", "key_rotated"
resource    resource type acted upon, e.g. "certificate", "user"
resource_id identifier of the specific resource (optional)
detail      free-form JSON detail blob
ip_address  originating IP
timestamp   UTC event time
"""

import uuid
from datetime import datetime, timezone
from extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action = db.Column(db.String(80), nullable=False, index=True)
    resource = db.Column(db.String(80), nullable=True)
    resource_id = db.Column(db.String(36), nullable=True)
    detail = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "detail": self.detail,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_id}>"
