"""Encryption utilities for secure credential storage.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
for encrypting sensitive data at rest.
"""

import base64
import hashlib
import logging
import secrets
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

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
    In production, ensure SECRET_KEY is a strong, unique value.

    Returns:
        Fernet instance for encryption operations
    """
    if settings.SECRET_KEY == "change-this-in-production-use-a-real-secret-key":
        logger.warning(
            "Using default SECRET_KEY for encryption. Set a strong SECRET_KEY in production!"
        )

    key = _derive_key_from_secret(settings.SECRET_KEY)
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded encrypted string (safe for database storage)
    """
    if not plaintext:
        return ""

    fernet = get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return encrypted.decode()


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


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.

    Args:
        length: Number of bytes (output will be 2x this in hex)

    Returns:
        Hex-encoded secure random token
    """
    return secrets.token_hex(length)


def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive value for display purposes.

    Args:
        value: The sensitive value to mask
        visible_chars: Number of characters to show at start and end

    Returns:
        Masked string like "abcd****efgh"
    """
    if not value or len(value) <= visible_chars * 2:
        return "*" * len(value) if value else ""

    return (
        f"{value[:visible_chars]}{'*' * (len(value) - visible_chars * 2)}{value[-visible_chars:]}"
    )
