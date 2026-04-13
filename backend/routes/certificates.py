"""
routes/certificates.py
-----------------------
Certificate management endpoints (protected).

POST   /certificates/issue              — issue a new certificate (admin/analyst)
GET    /certificates/<id>               — fetch certificate details (any auth)
POST   /certificates/<id>/revoke        — revoke a certificate (admin)
GET    /certificates/                   — list certificates (admin/analyst)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from services.certificate_service import issue_certificate, revoke_certificate
from services.audit_service import record_event
from models.certificate import Certificate
from utils.decorators import admin_required, analyst_required, viewer_required

cert_bp = Blueprint("certificates", __name__)


@cert_bp.route("/issue", methods=["POST"])
@analyst_required
def issue():
    data = request.get_json(silent=True) or {}
    owner_name = data.get("owner_name", "").strip()
    owner_email = data.get("owner_email", "").strip()

    if not owner_name or not owner_email:
        return jsonify({"error": "owner_name and owner_email are required"}), 400

    issued_by = get_jwt_identity()

    try:
        cert = issue_certificate(
            owner_name=owner_name,
            owner_email=owner_email,
            issued_by=issued_by,
            metadata=data.get("metadata"),
        )
    except ValueError:
        return jsonify({"error": "Certificate issuance failed. Check that an active signing key exists."}), 400

    record_event(
        "cert_issued",
        user_id=issued_by,
        resource="certificate",
        resource_id=cert.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"certificate": cert.to_dict()}), 201


@cert_bp.route("/<cert_id>", methods=["GET"])
@viewer_required
def get_cert(cert_id):
    cert = Certificate.query.get(cert_id)
    if cert is None:
        return jsonify({"error": "Certificate not found"}), 404
    return jsonify({"certificate": cert.to_dict()}), 200


@cert_bp.route("/<cert_id>/revoke", methods=["POST"])
@admin_required
def revoke(cert_id):
    revoked_by = get_jwt_identity()
    try:
        cert = revoke_certificate(cert_id, revoked_by=revoked_by)
    except ValueError:
        return jsonify({"error": "Revocation failed. Certificate may not exist or is already revoked."}), 400

    record_event(
        "cert_revoked",
        user_id=revoked_by,
        resource="certificate",
        resource_id=cert_id,
        ip_address=request.remote_addr,
    )
    return jsonify({"certificate": cert.to_dict()}), 200


@cert_bp.route("/", methods=["GET"])
@analyst_required
def list_certs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    query = Certificate.query.order_by(Certificate.issued_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "certificates": [c.to_dict() for c in paginated.items],
            "total": paginated.total,
            "page": page,
            "pages": paginated.pages,
        }
    ), 200
