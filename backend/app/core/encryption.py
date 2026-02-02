"""Secure encryption utilities for credential storage.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
with PBKDF2 key derivation for encrypting sensitive data at rest.

Security features:
- Separate ENCRYPTION_KEY from SECRET_KEY (key separation)
- PBKDF2 with 600,000 iterations (OWASP 2023 recommendation)
- Unique salt per encrypted value (stored with ciphertext)
- HMAC verification prevents tampering
"""

import base64
import logging
import os
import secrets
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings

logger = logging.getLogger(__name__)

# Salt length in bytes (16 bytes = 128 bits, recommended minimum)
SALT_LENGTH = 16

# Separator between salt and ciphertext in stored value
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


def _check_key_security() -> None:
    """Log warnings if using default/weak encryption keys."""
    if settings.ENCRYPTION_KEY == "change-this-encryption-key-in-production":
        logger.warning("Using default ENCRYPTION_KEY! Set a strong unique key in production.")
    if settings.ENCRYPTION_KEY == settings.SECRET_KEY:
        logger.warning("ENCRYPTION_KEY equals SECRET_KEY! Use separate keys in production.")


@lru_cache
def _get_encryption_config() -> tuple[str, int]:
    """Get cached encryption configuration and log warnings once."""
    _check_key_security()
    return settings.ENCRYPTION_KEY, settings.ENCRYPTION_ITERATIONS


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string with a unique salt.

    The output format is: base64(salt) + "$" + base64(ciphertext)
    This allows each encrypted value to have its own derived key.

    Args:
        plaintext: The string to encrypt

    Returns:
        Salt and encrypted ciphertext, safe for database storage
    """
    if not plaintext:
        return ""

    encryption_key, iterations = _get_encryption_config()

    # Generate unique salt for this value
    salt = os.urandom(SALT_LENGTH)

    # Derive key using PBKDF2
    key = _derive_key(encryption_key, salt, iterations)
    fernet = Fernet(key)

    # Encrypt the plaintext
    ciphertext = fernet.encrypt(plaintext.encode())

    # Combine salt and ciphertext for storage
    salt_b64 = base64.urlsafe_b64encode(salt)
    combined = salt_b64 + SEPARATOR + ciphertext

    return combined.decode()


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


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.

    Args:
        length: Number of bytes (output will be longer due to encoding)

    Returns:
        URL-safe base64-encoded secure random token
    """
    return secrets.token_urlsafe(length)


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
