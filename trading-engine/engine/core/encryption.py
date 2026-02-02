"""Secure encryption utilities for credential storage.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
with PBKDF2 key derivation for decrypting broker credentials.

Must use the same ENCRYPTION_KEY and algorithm as the backend.
"""

import base64
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from engine.config import settings

logger = logging.getLogger(__name__)

# Separator between salt and ciphertext (must match backend)
SEPARATOR = b"$"


def _derive_key(secret: str, salt: bytes, iterations: int) -> bytes:
    """Derive a Fernet key using PBKDF2.

    Args:
        secret: The encryption key from settings
        salt: Random salt for this derivation
        iterations: Number of PBKDF2 iterations

    Returns:
        Base64-url encoded 32-byte key for Fernet
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    key_bytes = kdf.derive(secret.encode())
    return base64.urlsafe_b64encode(key_bytes)


@lru_cache
def _get_encryption_config() -> tuple[str, int]:
    """Get cached encryption configuration."""
    if settings.ENCRYPTION_KEY == "change-this-encryption-key-in-production":
        logger.warning("Using default ENCRYPTION_KEY! Set a strong unique key in production.")
    return settings.ENCRYPTION_KEY, settings.ENCRYPTION_ITERATIONS


def decrypt_value(stored_value: str) -> str:
    """Decrypt a stored encrypted value.

    Args:
        stored_value: The salt$ciphertext string from storage

    Returns:
        Decrypted plaintext string

    Raises:
        ValueError: If decryption fails (invalid token, corrupted data, or wrong key)
    """
    if not stored_value:
        return ""

    try:
        encryption_key, iterations = _get_encryption_config()

        # Split salt and ciphertext
        parts = stored_value.encode().split(SEPARATOR, 1)
        if len(parts) != 2:
            raise ValueError("Invalid encrypted value format")

        salt_b64, ciphertext = parts
        salt = base64.urlsafe_b64decode(salt_b64)

        # Derive the same key using stored salt
        key = _derive_key(encryption_key, salt, iterations)
        fernet = Fernet(key)

        # Decrypt
        decrypted = fernet.decrypt(ciphertext)
        return decrypted.decode()

    except InvalidToken as e:
        logger.error("Decryption failed: invalid token (wrong key or corrupted data)")
        raise ValueError("Decryption failed: invalid or corrupted data") from e
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise ValueError(f"Decryption failed: {e}") from e
