"""
services/key_service.py
------------------------
Manages RSA key pairs for signing certificates and exports.

Public API
----------
generate_key_pair(label, created_by)  — generate, persist, and store a new RSA key pair
get_active_key()                      — return the single active RSAKey or None
rotate_key(label, created_by)         — generate a new key, retire the old active key
sign_payload(data, rsa_key)           — RSA-sign a string payload; return hex signature
verify_signature(data, signature_hex, rsa_key) → bool
"""

from __future__ import annotations

import os
import uuid
import hashlib
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

from extensions import db
from models.rsa_key import RSAKey
from config import get_config


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _private_key_path(key_id: str) -> str:
    cfg = get_config()
    os.makedirs(cfg.RSA_KEY_STORAGE_PATH, exist_ok=True)
    return os.path.join(cfg.RSA_KEY_STORAGE_PATH, f"{key_id}_private.pem")


def _load_private_key(path: str):
    with open(path, "rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None)


# --------------------------------------------------------------------------- #
# Public API                                                                    #
# --------------------------------------------------------------------------- #

def generate_key_pair(
    label: str,
    created_by: str | None = None,
) -> RSAKey:
    """
    Generate a new RSA key pair, save the private key to the filesystem,
    and persist the public key + metadata to the database.
    """
    cfg = get_config()
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=cfg.RSA_KEY_SIZE,
    )
    public_key = private_key.public_key()

    key_id = str(uuid.uuid4())
    private_path = _private_key_path(key_id)

    # Write private key PEM (no password — add passphrase for production)
    with open(private_path, "wb") as fh:
        fh.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    os.chmod(private_path, 0o600)

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    rsa_key = RSAKey(
        id=key_id,
        label=label,
        public_key_pem=public_pem,
        private_key_path=private_path,
        algorithm="RSA",
        key_size=cfg.RSA_KEY_SIZE,
        status="active",
        created_by=created_by,
    )
    db.session.add(rsa_key)
    db.session.commit()
    return rsa_key


def get_active_key() -> RSAKey | None:
    """Return the current active RSA key, or None if none exists."""
    return RSAKey.query.filter_by(status="active").first()


def rotate_key(label: str, created_by: str | None = None) -> RSAKey:
    """
    Retire the current active key and generate a fresh one.
    Returns the new RSAKey record.
    """
    old_key = get_active_key()
    if old_key:
        old_key.status = "rotated"
        old_key.rotated_at = datetime.now(timezone.utc)
        db.session.commit()
    return generate_key_pair(label, created_by)


def sign_payload(data: str, rsa_key: RSAKey) -> str:
    """
    Sign *data* with the private key referenced by *rsa_key*.
    Returns the hex-encoded signature string.
    """
    private_key = _load_private_key(rsa_key.private_key_path)
    signature_bytes = private_key.sign(
        data.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return signature_bytes.hex()


def verify_signature(data: str, signature_hex: str, rsa_key: RSAKey) -> bool:
    """
    Verify that *signature_hex* is a valid RSA-PSS signature over *data*
    produced by the private key paired with *rsa_key*.

    Returns True on valid, False otherwise.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    public_key = load_pem_public_key(rsa_key.public_key_pem.encode())
    try:
        public_key.verify(
            bytes.fromhex(signature_hex),
            data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False
