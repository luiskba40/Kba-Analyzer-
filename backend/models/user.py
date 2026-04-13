"""
models/user.py
--------------
Represents a KBA platform user.

Columns
-------
id          UUID primary key
username    unique login name
email       unique email
password    bcrypt hash stored as text
role        one of: admin | analyst | viewer
is_active   soft-delete / account disable flag
created_at  record creation timestamp
"""

import uuid
from datetime import datetime, timezone
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(
        db.String(20),
        nullable=False,
        default="viewer",
        # allowed values enforced at the service layer
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ---------------------------------------------------------------- helpers
    def set_password(self, plain: str) -> None:
        self.password_hash = generate_password_hash(plain)

    def check_password(self, plain: str) -> bool:
        return check_password_hash(self.password_hash, plain)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
