"""
routes/auth.py
--------------
Authentication endpoints.

POST /auth/login    — validate credentials, return access + refresh tokens
POST /auth/refresh  — exchange a valid refresh token for a new access token
POST /auth/logout   — (stateless JWT) client-side logout hint

JWT claims include: sub (user_id), role
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

from models.user import User
from services.audit_service import record_event

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user: User | None = User.query.filter_by(username=username, is_active=True).first()

    if user is None or not user.check_password(password):
        record_event(
            "login_failed",
            detail={"username": username},
            ip_address=request.remote_addr,
        )
        return jsonify({"error": "Invalid credentials"}), 401

    additional_claims = {"role": user.role}
    access_token = create_access_token(
        identity=user.id, additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        identity=user.id, additional_claims=additional_claims
    )

    record_event(
        "login_success",
        user_id=user.id,
        resource="user",
        resource_id=user.id,
        ip_address=request.remote_addr,
    )

    return jsonify(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        }
    ), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role", "viewer")

    access_token = create_access_token(
        identity=identity, additional_claims={"role": role}
    )
    return jsonify({"access_token": access_token}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Stateless JWT logout: the client must discard the tokens.
    For server-side revocation, add token IDs to a Redis blocklist here.
    """
    return jsonify({"message": "Logged out. Please discard your tokens."}), 200
