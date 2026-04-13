"""
utils/decorators.py
-------------------
Convenience decorators that combine JWT validation with role enforcement.

Available decorators
--------------------
admin_required       — only the "admin" role
analyst_required     — "admin" or "analyst"
viewer_required      — any authenticated user (admin | analyst | viewer)
"""

from middleware.auth_middleware import jwt_required_with_roles

# Strict role gating
admin_required = jwt_required_with_roles(["admin"])
analyst_required = jwt_required_with_roles(["admin", "analyst"])
viewer_required = jwt_required_with_roles(["admin", "analyst", "viewer"])
