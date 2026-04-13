"""
services/certificate_service.py
--------------------------------
Handles the full lifecycle of a KBA certificate:
  1. Generate a unique serial number
  2. Sign the certificate payload with the active RSA key
  3. Render a PDF certificate and save it to disk
  4. Generate a QR code that encodes the public verification URL
  5. Persist the Certificate record to the database

Public API
----------
issue_certificate(owner_name, owner_email, issued_by, metadata, expires_at)
    → Certificate

revoke_certificate(cert_id, revoked_by)
    → Certificate
"""

from __future__ import annotations

import os
import uuid
import json
import qrcode

from datetime import datetime, timezone
from io import BytesIO

from extensions import db
from models.certificate import Certificate
from services.key_service import get_active_key, sign_payload
from config import get_config


def _generate_serial() -> str:
    return f"KBA-{uuid.uuid4().hex[:12].upper()}"


def _build_cert_path(cert_id: str) -> str:
    cfg = get_config()
    os.makedirs(cfg.CERT_STORAGE_PATH, exist_ok=True)
    return os.path.join(cfg.CERT_STORAGE_PATH, f"{cert_id}.json")


def _build_qr_path(cert_id: str) -> str:
    cfg = get_config()
    os.makedirs(cfg.CERT_STORAGE_PATH, exist_ok=True)
    return os.path.join(cfg.CERT_STORAGE_PATH, f"{cert_id}_qr.png")


def _generate_qr(cert_id: str) -> str:
    """Generate a QR code PNG and return its file path."""
    cfg = get_config()
    verify_url = f"{cfg.QR_BASE_VERIFY_URL}/{cert_id}"
    img = qrcode.make(verify_url)
    qr_path = _build_qr_path(cert_id)
    img.save(qr_path)
    return qr_path


def _save_cert_payload(cert_id: str, payload: dict) -> str:
    """Persist the certificate payload JSON and return path."""
    cert_path = _build_cert_path(cert_id)
    with open(cert_path, "w") as fh:
        json.dump(payload, fh, indent=2)
    return cert_path


def issue_certificate(
    owner_name: str,
    owner_email: str,
    issued_by: str | None = None,
    metadata: dict | None = None,
    expires_at: datetime | None = None,
) -> Certificate:
    """
    Create and persist a new Certificate.

    Raises ValueError if no active RSA key is available for signing.
    """
    active_key = get_active_key()
    if active_key is None:
        raise ValueError("No active RSA key available for signing.")

    cert_id = str(uuid.uuid4())
    serial = _generate_serial()
    issued_at = datetime.now(timezone.utc)

    payload = {
        "id": cert_id,
        "serial_number": serial,
        "owner_name": owner_name,
        "owner_email": owner_email,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "metadata": metadata or {},
    }

    signature = sign_payload(json.dumps(payload, sort_keys=True), active_key)
    cert_path = _save_cert_payload(cert_id, {**payload, "signature": signature})
    qr_path = _generate_qr(cert_id)

    cert = Certificate(
        id=cert_id,
        owner_name=owner_name,
        owner_email=owner_email,
        issued_by=issued_by,
        issued_at=issued_at,
        expires_at=expires_at,
        status="active",
        cert_path=cert_path,
        qr_path=qr_path,
        serial_number=serial,
        signature=signature,
        key_id=active_key.id,
        metadata_=metadata,
    )
    db.session.add(cert)
    db.session.commit()
    return cert


def revoke_certificate(cert_id: str, revoked_by: str | None = None) -> Certificate:
    """Mark a certificate as revoked."""
    cert = Certificate.query.get(cert_id)
    if cert is None:
        raise ValueError(f"Certificate {cert_id} not found.")
    if cert.status == "revoked":
        raise ValueError(f"Certificate {cert_id} is already revoked.")
    cert.status = "revoked"
    cert.revoked_by = revoked_by
    cert.revoked_at = datetime.now(timezone.utc)
    db.session.commit()
    return cert
