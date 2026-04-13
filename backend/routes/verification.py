"""
routes/verification.py
-----------------------
Public QR verification endpoint — no authentication required.

GET /verify/<cert_id>   — check whether a certificate is valid and return its metadata
"""

import json
import os

from flask import Blueprint, jsonify
from models.certificate import Certificate
from models.rsa_key import RSAKey
from services.key_service import verify_signature

verify_bp = Blueprint("verification", __name__)


@verify_bp.route("/<cert_id>", methods=["GET"])
def verify_certificate(cert_id):
    """
    Public verification.  Returned data is intentionally limited to what
    a relying party needs to confirm authenticity.
    """
    cert = Certificate.query.get(cert_id)
    if cert is None:
        return jsonify({"valid": False, "error": "Certificate not found"}), 404

    if cert.status != "active":
        return jsonify(
            {
                "valid": False,
                "status": cert.status,
                "serial_number": cert.serial_number,
                "owner_name": cert.owner_name,
            }
        ), 200

    # Optionally verify signature if we have the cert payload on disk
    signature_ok = None
    if cert.cert_path and os.path.exists(cert.cert_path) and cert.signature and cert.key_id:
        rsa_key: RSAKey | None = RSAKey.query.get(cert.key_id)
        if rsa_key:
            with open(cert.cert_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            # Re-build the payload that was signed (without the signature field)
            payload_for_verify = {k: v for k, v in raw.items() if k != "signature"}
            signature_ok = verify_signature(
                json.dumps(payload_for_verify, sort_keys=True),
                cert.signature,
                rsa_key,
            )

    return jsonify(
        {
            "valid": True,
            "signature_ok": signature_ok,
            "serial_number": cert.serial_number,
            "owner_name": cert.owner_name,
            "owner_email": cert.owner_email,
            "issued_at": cert.issued_at.isoformat(),
            "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
            "status": cert.status,
        }
    ), 200
