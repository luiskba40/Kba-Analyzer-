"""
routes/keys.py
--------------
RSA key management endpoints (admin only).

POST /keys/generate         — generate a new RSA key pair
GET  /keys/                 — list key inventory
GET  /keys/<id>             — get key details (includes public key PEM)
POST /keys/rotate           — rotate the active key
POST /keys/verify-signature — verify a signature against a given key
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from services.key_service import generate_key_pair, get_active_key, rotate_key, verify_signature
from services.audit_service import record_event
from models.rsa_key import RSAKey
from utils.decorators import admin_required

keys_bp = Blueprint("keys", __name__)


@keys_bp.route("/generate", methods=["POST"])
@admin_required
def generate():
    data = request.get_json(silent=True) or {}
    label = data.get("label", "").strip()
    if not label:
        return jsonify({"error": "label is required"}), 400

    created_by = get_jwt_identity()
    rsa_key = generate_key_pair(label=label, created_by=created_by)

    record_event(
        "key_generated",
        user_id=created_by,
        resource="rsa_key",
        resource_id=rsa_key.id,
        ip_address=request.remote_addr,
    )
    return jsonify({"key": rsa_key.to_dict(include_public_key=True)}), 201


@keys_bp.route("/", methods=["GET"])
@admin_required
def list_keys():
    keys = RSAKey.query.order_by(RSAKey.created_at.desc()).all()
    return jsonify({"keys": [k.to_dict() for k in keys]}), 200


@keys_bp.route("/<key_id>", methods=["GET"])
@admin_required
def get_key(key_id):
    key = RSAKey.query.get(key_id)
    if key is None:
        return jsonify({"error": "Key not found"}), 404
    return jsonify({"key": key.to_dict(include_public_key=True)}), 200


@keys_bp.route("/rotate", methods=["POST"])
@admin_required
def rotate():
    data = request.get_json(silent=True) or {}
    label = data.get("label", "rotated-key").strip()
    created_by = get_jwt_identity()

    new_key = rotate_key(label=label, created_by=created_by)

    record_event(
        "key_rotated",
        user_id=created_by,
        resource="rsa_key",
        resource_id=new_key.id,
        ip_address=request.remote_addr,
    )
    return jsonify({"message": "Key rotated", "new_key": new_key.to_dict()}), 200


@keys_bp.route("/verify-signature", methods=["POST"])
def verify():
    """
    Public-ish endpoint: verify a payload signature against a specific key.

    Body: { "key_id": "...", "data": "...", "signature": "<hex>" }
    """
    data = request.get_json(silent=True) or {}
    key_id = data.get("key_id", "")
    payload_data = data.get("data", "")
    sig_hex = data.get("signature", "")

    if not key_id or not payload_data or not sig_hex:
        return jsonify({"error": "key_id, data, and signature are required"}), 400

    rsa_key = RSAKey.query.get(key_id)
    if rsa_key is None:
        return jsonify({"error": "Key not found"}), 404

    valid = verify_signature(payload_data, sig_hex, rsa_key)
    return jsonify({"valid": valid}), 200
