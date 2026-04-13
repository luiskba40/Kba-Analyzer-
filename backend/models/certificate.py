"""
models/certificate.py
---------------------
Represents an issued KBA certificate.

Columns
-------
id              UUID primary key / certificate ID
owner_name      human-readable name printed on the certificate
owner_email     recipient email
issued_by       user_id of the issuing admin/analyst
issued_at       issuance timestamp
expires_at      optional expiry
status          active | revoked | expired
cert_path       filesystem path to the generated PDF
qr_path         filesystem path to the QR code PNG
serial_number   human-readable serial
signature       RSA signature (hex) over the certificate payload
key_id          FK → rsa_keys used for signing
"""

import uuid
from datetime import datetime, timezone
from extensions import db


class Certificate(db.Model):
    __tablename__ = "certificates"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_name = db.Column(db.String(200), nullable=False)
    owner_email = db.Column(db.String(120), nullable=False, index=True)
    issued_by = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    issued_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    cert_path = db.Column(db.Text, nullable=True)
    qr_path = db.Column(db.Text, nullable=True)
    serial_number = db.Column(db.String(50), unique=True, nullable=False)
    signature = db.Column(db.Text, nullable=True)
    key_id = db.Column(
        db.String(36), db.ForeignKey("rsa_keys.id", ondelete="SET NULL"), nullable=True
    )
    revoked_by = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    metadata_ = db.Column("metadata", db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_name": self.owner_name,
            "owner_email": self.owner_email,
            "issued_by": self.issued_by,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
            "serial_number": self.serial_number,
            "key_id": self.key_id,
            "revoked_by": self.revoked_by,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }

    def __repr__(self) -> str:
        return f"<Certificate {self.serial_number} [{self.status}]>"
