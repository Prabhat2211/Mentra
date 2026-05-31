from __future__ import annotations

import base64
import os
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings


def get_encryption_key() -> bytes:
    master_key = settings.encryption_master_key
    if not master_key:
        raise RuntimeError(
            "ENCRYPTION_MASTER_KEY is not set in .env. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    # Use PBKDF2 to derive a proper key from the master key
    salt = b"yuno_salt_2024"  # In production, use a random salt per encryption
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))


def encrypt_value(plaintext: str) -> bytes:
    if not plaintext:
        return b""
    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.encrypt(plaintext.encode())


def decrypt_value(encrypted_data: bytes) -> str:
    if not encrypted_data:
        return ""
    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data).decode()
