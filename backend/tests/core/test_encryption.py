"""Tests for secure encryption utilities."""

from unittest.mock import MagicMock, patch

import pytest


# Mock settings before importing encryption module
@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests."""
    mock = MagicMock()
    mock.ENCRYPTION_KEY = "test-encryption-key-for-unit-tests"
    mock.ENCRYPTION_ITERATIONS = 1000  # Lower for faster tests
    mock.SECRET_KEY = "different-secret-key"

    with patch("app.core.encryption.settings", mock):
        # Clear the lru_cache
        from app.core.encryption import _get_encryption_config

        _get_encryption_config.cache_clear()
        yield mock
        _get_encryption_config.cache_clear()


class TestEncryption:
    """Test encryption and decryption functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypted values can be decrypted."""
        from app.core.encryption import decrypt_value, encrypt_value

        plaintext = "my-secret-api-key-12345"
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext  # Should be different

    def test_encrypt_produces_different_output_each_time(self):
        """Test that same plaintext produces different ciphertext (due to salt)."""
        from app.core.encryption import encrypt_value

        plaintext = "same-value"
        encrypted1 = encrypt_value(plaintext)
        encrypted2 = encrypt_value(plaintext)

        # Different salts should produce different ciphertexts
        assert encrypted1 != encrypted2

    def test_encrypted_format_contains_separator(self):
        """Test that encrypted value contains salt separator."""
        from app.core.encryption import encrypt_value

        encrypted = encrypt_value("test-value")

        # Should contain the $ separator
        assert "$" in encrypted

    def test_decrypt_empty_string(self):
        """Test decrypting empty string returns empty string."""
        from app.core.encryption import decrypt_value

        assert decrypt_value("") == ""
        assert decrypt_value(None) == ""

    def test_encrypt_empty_string(self):
        """Test encrypting empty string returns empty string."""
        from app.core.encryption import encrypt_value

        assert encrypt_value("") == ""

    def test_decrypt_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        from app.core.encryption import decrypt_value

        with pytest.raises(ValueError, match="Invalid encrypted value format"):
            decrypt_value("no-separator-here")

    def test_decrypt_corrupted_data_raises_error(self):
        """Test that corrupted ciphertext raises ValueError."""
        from app.core.encryption import decrypt_value

        # Valid format but corrupted ciphertext
        corrupted = "YWJjZGVmZ2hpamtsbW5vcA==$corrupted-ciphertext"

        with pytest.raises(ValueError):
            decrypt_value(corrupted)

    def test_decrypt_wrong_key_raises_error(self, mock_settings):
        """Test that wrong key raises ValueError."""
        from app.core.encryption import _get_encryption_config, decrypt_value, encrypt_value

        # Encrypt with current key
        encrypted = encrypt_value("secret-data")

        # Change the key
        mock_settings.ENCRYPTION_KEY = "different-key-now"
        _get_encryption_config.cache_clear()

        # Should fail to decrypt
        with pytest.raises(ValueError):
            decrypt_value(encrypted)

    def test_unicode_values(self):
        """Test encryption of unicode strings."""
        from app.core.encryption import decrypt_value, encrypt_value

        plaintext = "日本語テスト 🔐 émojis"
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)

        assert decrypted == plaintext

    def test_long_values(self):
        """Test encryption of long strings."""
        from app.core.encryption import decrypt_value, encrypt_value

        plaintext = "x" * 10000
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)

        assert decrypted == plaintext


class TestSecureToken:
    """Test secure token generation."""

    def test_generate_token_length(self):
        """Test that generated tokens have expected length."""
        from app.core.encryption import generate_secure_token

        token = generate_secure_token(32)
        # URL-safe base64 encoding: 32 bytes -> ~43 chars
        assert len(token) >= 32

    def test_generate_token_uniqueness(self):
        """Test that generated tokens are unique."""
        from app.core.encryption import generate_secure_token

        tokens = [generate_secure_token(32) for _ in range(100)]
        assert len(set(tokens)) == 100  # All unique


class TestMaskSensitiveValue:
    """Test value masking function."""

    def test_mask_normal_value(self):
        """Test masking a normal length value."""
        from app.core.encryption import mask_sensitive_value

        masked = mask_sensitive_value("abcdefghijkl", visible_chars=4)
        assert masked == "abcd****ijkl"

    def test_mask_short_value(self):
        """Test masking a short value shows all asterisks."""
        from app.core.encryption import mask_sensitive_value

        masked = mask_sensitive_value("short", visible_chars=4)
        assert masked == "*****"

    def test_mask_empty_value(self):
        """Test masking empty value."""
        from app.core.encryption import mask_sensitive_value

        assert mask_sensitive_value("") == ""
        assert mask_sensitive_value(None) == ""
