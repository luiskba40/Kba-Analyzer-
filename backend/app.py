"""
app.py
------
Flask application factory for KBA Core.

Calling create_app() returns a fully configured Flask application with:
  • SQLAlchemy + Flask-Migrate
  • Redis connection
  • JWT manager
  • CORS
  • All blueprints registered
  • Request-logging middleware attached
"""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()  # load .env before anything reads os.environ

from config import get_config
from extensions import db, migrate, jwt, init_redis


def create_app() -> Flask:
    app = Flask(__name__)

    # ---------------------------------------------------------------- config
    cfg = get_config()
    app.config.from_object(cfg)

    # ---------------------------------------------------------- extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    with app.app_context():
        init_redis()

        # Import models so Alembic can detect them
        from models import user, audit_log, certificate, job, rsa_key  # noqa: F401

        # -------------------------------------------------------- blueprints
        from routes.health import health_bp
        from routes.auth import auth_bp
        from routes.certificates import cert_bp
        from routes.operations import ops_bp
        from routes.keys import keys_bp
        from routes.verification import verify_bp

        app.register_blueprint(health_bp)
        app.register_blueprint(auth_bp, url_prefix="/auth")
        app.register_blueprint(cert_bp, url_prefix="/certificates")
        app.register_blueprint(ops_bp, url_prefix="/operations")
        app.register_blueprint(keys_bp, url_prefix="/keys")
        app.register_blueprint(verify_bp, url_prefix="/verify")

        # -------------------------------------------------- middleware hooks
        from middleware.logging_middleware import register_logging_middleware
        register_logging_middleware(app)

    return app


if __name__ == "__main__":
    application = create_app()
    port = int(os.environ.get("PORT", 5000))
    application.run(host="0.0.0.0", port=port)
