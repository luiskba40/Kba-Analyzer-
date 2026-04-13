"""
extensions.py
-------------
Initialises shared Flask extensions as module-level singletons so they
can be imported by models and other modules without creating circular
imports.  Each extension is bound to the actual Flask app inside the
application factory (app.py).
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
import redis as _redis_lib
from config import get_config

# SQLAlchemy ORM instance — imported by every model
db = SQLAlchemy()

# Alembic-based database migration helper
migrate = Migrate()

# JWT token manager
jwt = JWTManager()

# Redis connection pool; initialised lazily in init_redis()
redis_client: _redis_lib.Redis | None = None


def init_redis() -> _redis_lib.Redis:
    """Create (or return) a Redis client from the app config."""
    global redis_client
    if redis_client is None:
        cfg = get_config()
        redis_client = _redis_lib.from_url(
            cfg.REDIS_URL,
            decode_responses=True,
        )
    return redis_client
