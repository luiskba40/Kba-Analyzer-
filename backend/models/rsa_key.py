"""
models/rsa_key.py
-----------------
Inventory record for RSA key pairs managed by KBA Core.

The private key PEM is stored on the filesystem (path in private_key_path);
only the public key PEM is stored inline for quick lookup.  Key rotation
is handled by creating a new active record and marking the old one as
rotated.

Columns
-------
id               UUID primary key
label            human-readable name, e.g. "cert-signing-2024"
public_key_pem   public key in PEM format
private_key_path absolute filesystem path to encrypted private key
algorithm        RSA | EC  (RSA for now)
key_size         2048 | 4096
status           active | rotated | revoked
created_at       creation timestamp
rotated_at       timestamp when key was rotated away
created_by       user_id of admin who created the key
"""

import uuid
from datetime import datetime, timezone
from extensions import db


class RSAKey(db.Model):
    __tablename__ = "rsa_keys"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    label = db.Column(db.String(120), nullable=False)
    public_key_pem = db.Column(db.Text, nullable=False)
    private_key_path = db.Column(db.Text, nullable=False)
    algorithm = db.Column(db.String(10), nullable=False, default="RSA")
    key_size = db.Column(db.Integer, nullable=False, default=2048)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    rotated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def to_dict(self, include_public_key: bool = False) -> dict:
        data = {
            "id": self.id,
            "label": self.label,
            "algorithm": self.algorithm,
            "key_size": self.key_size,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "rotated_at": self.rotated_at.isoformat() if self.rotated_at else None,
            "created_by": self.created_by,
        }
        if include_public_key:
            data["public_key_pem"] = self.public_key_pem
        return data

    def __repr__(self) -> str:
        return f"<RSAKey {self.label} [{self.status}]>"
