"""Encryption utilities for secure credential storage.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
for decrypting broker credentials stored by the backend.
"""

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from engine.config import settings

logger = logging.getLogger(__name__)


def _derive_key_from_secret(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from the application secret.

    Uses SHA-256 to derive a consistent key from the secret.
    The key is base64-url encoded as required by Fernet.

    Args:
        secret: The application secret key

    Returns:
        Base64-url encoded 32-byte key for Fernet
    """
    # Use SHA-256 to get exactly 32 bytes
    key_bytes = hashlib.sha256(secret.encode()).digest()
    # Fernet requires base64-url encoded key
    return base64.urlsafe_b64encode(key_bytes)


@lru_cache
def get_fernet() -> Fernet:
    """Get cached Fernet instance for encryption/decryption.

    Uses the application SECRET_KEY to derive the encryption key.
    Must match the key used by the backend for encryption.

    Returns:
        Fernet instance for decryption operations
    """
    if settings.SECRET_KEY == "change-this-in-production-use-a-real-secret-key":
        logger.warning(
            "Using default SECRET_KEY for encryption. Set a strong SECRET_KEY in production!"
        )

    key = _derive_key_from_secret(settings.SECRET_KEY)
    return Fernet(key)


def decrypt_value(ciphertext: str) -> str:
    """Decrypt an encrypted string.

    Args:
        ciphertext: Base64-encoded encrypted string

    Returns:
        Decrypted plaintext string

    Raises:
        ValueError: If decryption fails (invalid token or corrupted data)
    """
    if not ciphertext:
        return ""

    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken as e:
        logger.error("Failed to decrypt value: invalid token or corrupted data")
        raise ValueError("Decryption failed: invalid or corrupted data") from e
