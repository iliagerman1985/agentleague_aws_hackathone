"""JWT utilities for token validation and user authentication."""

from datetime import UTC, datetime
from typing import Any

import requests
from jose import JWTError
from jose import jwt as jose_jwt
from jose.constants import ALGORITHMS

from common.core.config_service import ConfigService
from common.utils.utils import get_logger
from shared_db.schemas.auth import TokenData

logger = get_logger(__name__)

# Initialize config service
config_service = ConfigService()


class JWTValidator:
    """JWT token validator for Cognito tokens with dev mode fallback"""

    def __init__(self) -> None:
        config_service = ConfigService()
        self.cognito_config = config_service.get_cognito_config()
        self.is_localstack = config_service.is_localstack_enabled()
        self.is_development = config_service.is_development()
        self._jwks_cache: dict[str, Any] | None = None

    def _get_jwks_url(self) -> str:
        """Get the JWKS URL for token validation"""
        # AWS Cognito JWKS endpoint
        region = self.cognito_config["region"]
        user_pool_id = self.cognito_config["user_pool_id"]
        return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"

    def _get_jwks(self) -> dict[str, Any]:
        """Get JSON Web Key Set (JWKS) for token validation"""
        if self._jwks_cache is None:
            try:
                jwks_url = self._get_jwks_url()
                response = requests.get(jwks_url, timeout=10)
                response.raise_for_status()
                self._jwks_cache = response.json()
                logger.info("Successfully fetched JWKS")
            except Exception as e:
                logger.exception("Failed to fetch JWKS")
                raise Exception("Failed to fetch JWKS for token validation") from e

        # At this point, _jwks_cache cannot be None because we either
        # have a previously cached value or we just set it (or raised an exception)
        assert self._jwks_cache is not None
        return self._jwks_cache

    def _get_signing_key(self, token_header: dict[str, Any]) -> str:
        """Get the signing key for token validation"""
        jwks = self._get_jwks()

        # Find the key that matches the token's kid
        kid = token_header.get("kid")
        if not kid:
            raise Exception("Token header missing 'kid' field")

        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                # Convert JWK to PEM format
                from jose.backends.rsa_backend import RSAKey

                return RSAKey(key, ALGORITHMS.RS256).to_pem().decode("utf-8")

        raise Exception(f"Unable to find signing key with kid: {kid}")

    def validate_token(self, token: str) -> TokenData:
        """Validate JWT token and return token data.
        Tries Cognito validation first, then falls back to local token validation in dev mode.
        """
        # First, try to validate as Cognito token
        try:
            return self._validate_cognito_token(token)
        except Exception as cognito_error:
            logger.debug(f"Cognito token validation failed: {cognito_error}")

            # In development mode, try local token validation as fallback
            if self.is_development:
                try:
                    return self._validate_local_token(token)
                except Exception as local_error:
                    logger.debug(f"Local token validation failed: {local_error}")
                    raise Exception("Token validation failed: Invalid token format")
            else:
                # In production, only Cognito tokens are allowed
                raise Exception("Token validation failed: Invalid Cognito token")

    def _validate_cognito_token(self, token: str) -> TokenData:
        """Validate Cognito JWT token"""
        try:
            # Decode token header to get key ID
            unverified_header = jose_jwt.get_unverified_header(token)

            # Get signing key
            signing_key = self._get_signing_key(unverified_header)

            # Verify and decode token
            payload = jose_jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.cognito_config["client_id"],
                options={"verify_exp": True},
            )

            # Extract token data
            username = payload.get("cognito:username") or payload.get("username")
            user_sub = payload.get("sub")
            email = payload.get("email")

            # Verify token type
            token_use = payload.get("token_use")
            if token_use not in ["access", "id"]:
                raise Exception("Invalid token type")

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=UTC) < datetime.now(
                UTC,
            ):
                raise Exception("Token has expired")

            logger.debug(f"Cognito token validated successfully for user: {username}")

            return TokenData(username=username, user_sub=user_sub, email=email)

        except JWTError as e:
            logger.exception(f"Cognito JWT validation error: {e}")
            raise Exception("Invalid Cognito token")
        except Exception as e:
            logger.exception(f"Cognito token validation failed: {e}")
            raise Exception("Cognito token validation failed")

    def _validate_local_token(self, token: str) -> TokenData:
        """Validate local development token (only in dev mode)"""
        if not self.is_development:
            raise Exception("Local tokens not allowed in production")

        try:
            secret_key = config_service.get_secret_key()
            algorithm = config_service.get("security.algorithm", "HS256")

            payload = jose_jwt.decode(token, secret_key, algorithms=[algorithm])

            # Extract token data
            username = payload.get("username")
            user_sub = payload.get("user_sub")
            email = payload.get("email")

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=UTC) < datetime.now(
                UTC,
            ):
                raise Exception("Token has expired")

            logger.info(f"Local token validated successfully for user: {username}")

            return TokenData(username=username, user_sub=user_sub, email=email)

        except JWTError as e:
            logger.exception(f"Local token validation error: {e}")
            raise Exception("Invalid local token")
        except Exception as e:
            logger.exception(f"Local token validation failed: {e}")
            raise Exception("Local token validation failed")

    def decode_token_without_verification(self, token: str) -> dict[str, Any]:
        """Decode token without verification (for debugging)"""
        try:
            return jose_jwt.get_unverified_claims(token)
        except Exception as e:
            logger.exception(f"Failed to decode token: {e}")
            raise Exception("Failed to decode token")


# Global instance
jwt_validator = JWTValidator()


def create_access_token(
    data: dict[str, Any],
    expires_delta: int | None = None,
) -> str:
    """Create a local access token (for development only)"""
    if not config_service.is_development():
        raise Exception("Local token creation not allowed in production")

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC).timestamp() + expires_delta
    else:
        expire = datetime.now(UTC).timestamp() + 7200  # 2 hours default

    to_encode.update({"exp": expire})

    # Ensure required fields are present
    if "username" not in to_encode:
        raise Exception("Username is required for local token")

    # Use the secret key from configuration
    secret_key = config_service.get_secret_key()
    algorithm = config_service.get("security.algorithm", "HS256")

    encoded_jwt = jose_jwt.encode(to_encode, secret_key, algorithm=algorithm)
    logger.info(f"Created local access token for user: {to_encode.get('username')}")
    return encoded_jwt


def verify_local_token(token: str) -> dict[str, Any]:
    """Verify a locally created token"""
    try:
        secret_key = config_service.get_secret_key()
        algorithm = config_service.get("security.algorithm", "HS256")

        return jose_jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError as e:
        logger.exception(f"Local token validation error: {e}")
        raise Exception("Invalid local token")
