"""
config.py
---------
Centralised, environment-driven configuration for KBA Core.
All secrets and service URLs are read from environment variables so that
the same codebase works in development, staging, and production without
code changes.
"""

import os
import secrets
from datetime import timedelta


def _require_or_default(env_var: str, *, allow_default: bool = False) -> str:
    """Return the env var value.  In production, always require it to be set."""
    value = os.environ.get(env_var)
    if value:
        return value
    if allow_default:
        return secrets.token_hex(32)
    raise RuntimeError(
        f"Required environment variable '{env_var}' is not set. "
        "Set it before starting the application."
    )


class Config:
    # ------------------------------------------------------------------ Flask
    SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

    # ----------------------------------------------------------- PostgreSQL
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://kba_user:kba_pass@localhost:5432/kba_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # --------------------------------------------------------------- Redis
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # ----------------------------------------------------------------- JWT
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", secrets.token_hex(32))
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_EXPIRES_MINUTES", "60"))
    )
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(
        days=int(os.environ.get("JWT_REFRESH_EXPIRES_DAYS", "30"))
    )
    JWT_ALGORITHM: str = "HS256"

    # --------------------------------------------------------- Certificates
    CERT_STORAGE_PATH: str = os.environ.get("CERT_STORAGE_PATH", "/tmp/kba_certs")
    QR_BASE_VERIFY_URL: str = os.environ.get(
        "QR_BASE_VERIFY_URL", "http://localhost:5000/verify"
    )

    # ------------------------------------------------------------ RSA Keys
    RSA_KEY_SIZE: int = int(os.environ.get("RSA_KEY_SIZE", "2048"))
    RSA_KEY_STORAGE_PATH: str = os.environ.get(
        "RSA_KEY_STORAGE_PATH", "/tmp/kba_keys"
    )

    # -------------------------------------------------------------- Workers
    RQ_QUEUE_NAME: str = os.environ.get("RQ_QUEUE_NAME", "kba_jobs")
    RQ_MAX_RETRIES: int = int(os.environ.get("RQ_MAX_RETRIES", "3"))
    DEAD_LETTER_QUEUE_NAME: str = os.environ.get(
        "DEAD_LETTER_QUEUE_NAME", "kba_dead_letter"
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


# Map name → class so app factory can resolve via env var
_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config() -> Config:
    env = os.environ.get("FLASK_ENV", "default")
    return _CONFIG_MAP.get(env, DevelopmentConfig)()
