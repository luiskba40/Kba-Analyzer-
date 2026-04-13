"""
routes/health.py
----------------
Lightweight probes used by load-balancers and orchestration tools.

GET /health  — liveness probe (always 200 if Flask is running)
GET /status  — readiness probe (checks DB + Redis connectivity)
"""

from flask import Blueprint, jsonify
from extensions import db, init_redis

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    """Liveness probe — returns 200 as long as Flask is up."""
    return jsonify({"status": "ok"}), 200


@health_bp.route("/status", methods=["GET"])
def status():
    """Readiness probe — verifies DB and Redis are reachable."""
    checks: dict = {}

    # --- PostgreSQL ---
    try:
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # --- Redis ---
    try:
        redis = init_redis()
        redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    return jsonify({"status": "ok" if all_ok else "degraded", "checks": checks}), (200 if all_ok else 503)
