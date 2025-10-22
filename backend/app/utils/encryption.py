"""Encryption utilities for securing sensitive data like API keys."""

from cryptography.fernet import Fernet

from common.core.app_error import Errors
from common.core.config_service import ConfigService
from common.utils.utils import get_logger

logger = get_logger()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    fernet: Fernet

    def __init__(self) -> None:
        """Initialize encryption service with key from config service."""
        config_service = ConfigService()

        # Try to get encryption key from secrets using config service
        encryption_key = config_service.get("security.encryption_key")

        if not encryption_key:
            logger.warning("Encryption key not found in secrets, generating a new one for development")
            # Generate a new key for development (not recommended for production)
            encryption_key = Fernet.generate_key().decode()
            logger.warning(f"Generated encryption key: {encryption_key}")
            logger.warning("Please add this key to your secrets.yaml under security.encryption_key for production")

        try:
            # Fernet keys are always base64 encoded strings
            self.fernet = Fernet(encryption_key.encode())
            logger.info("Encryption service initialized successfully")
        except Exception:
            logger.exception("Failed to initialize encryption service")
            # Fall back to generating a new key
            new_key = Fernet.generate_key()
            self.fernet = Fernet(new_key)
            logger.warning(f"Using generated key: {new_key.decode()}")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Encrypted string (Fernet already returns base64-encoded data)
        """
        try:
            plaintext_bytes = plaintext.encode("utf-8")
            encrypted_bytes = self.fernet.encrypt(plaintext_bytes)
            # Fernet already returns base64-encoded data as bytes
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.exception("Encryption failed")
            raise ValueError("Failed to encrypt data") from e

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt encrypted data and return plaintext.

        Args:
            encrypted_data: Encrypted string (base64-encoded from Fernet)

        Returns:
            Decrypted plaintext string
        """
        try:
            # Fernet expects base64-encoded bytes
            encrypted_bytes = encrypted_data.encode("utf-8")
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.exception("Decryption failed")
            raise Errors.Generic.DECRYPTION_FAILED.create(cause=e) from e


# Global encryption service instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance.

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_api_key(api_key: str) -> str:
    """Convenience function to encrypt an API key.

    Args:
        api_key: Plain text API key

    Returns:
        Encrypted API key
    """
    return get_encryption_service().encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Convenience function to decrypt an API key.

    Args:
        encrypted_key: Encrypted API key

    Returns:
        Plain text API key
    """
    return get_encryption_service().decrypt(encrypted_key)
