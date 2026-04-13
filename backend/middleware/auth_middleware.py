"""
middleware/auth_middleware.py
-----------------------------
Provides:
  • jwt_required_with_roles(roles) — decorator that enforces JWT presence
    and optionally restricts to one or more roles.

Usage in a route:
    @cert_bp.route("/issue", methods=["POST"])
    @jwt_required_with_roles(["admin", "analyst"])
    def issue():
        ...
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def jwt_required_with_roles(roles: list[str] | None = None):
    """
    Decorator factory.

    Parameters
    ----------
    roles : list[str] | None
        Allowed roles.  Pass None (or []) to require only a valid JWT
        without role restriction.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if roles:
                claims = get_jwt()
                user_role = claims.get("role", "")
                if user_role not in roles:
                    return (
                        jsonify(
                            {
                                "error": "Forbidden",
                                "message": f"Required role: {roles}",
                            }
                        ),
                        403,
                    )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
