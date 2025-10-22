"""Shared encryption utilities for securing sensitive data like API keys.

Uses Fernet symmetric encryption. The key is read from ConfigService at
`security.encryption_key`. In test/dev, if no key is configured, a transient
key is generated so local flows don't break. For production, configure a
stable key in libs/common/secrets.yaml.
"""

from cryptography.fernet import Fernet

from common.core.config_service import ConfigService
from common.utils.utils import get_logger

logger = get_logger(__name__)


def _get_fernet() -> Fernet:
    config_service = ConfigService()
    key = config_service.get("security.encryption_key")
    if not key:
        # For local/test convenience only; log at warn so it's noticeable
        logger.warning(
            "Encryption key not found in secrets; generating a transient key (dev/test only)",
        )
        key = Fernet.generate_key().decode()
    try:
        return Fernet(str(key).encode())
    except Exception:
        logger.exception("Failed to construct Fernet from configured key; generating a new one")
        return Fernet(Fernet.generate_key())


def encrypt_api_key(api_key: str) -> str:
    """Encrypt a plaintext API key and return base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an encrypted API key and return plaintext."""
    f = _get_fernet()
    return f.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
