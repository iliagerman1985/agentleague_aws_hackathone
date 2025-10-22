"""Cognito service for handling authentication operations.
Supports both LocalStack (development) and AWS Cognito (production).
"""

import base64
import hashlib
import hmac
import json
import urllib.parse
from typing import Any

import boto3
import httpx
from botocore.exceptions import ClientError

from common.core.config_service import ConfigService
from common.core.exceptions import CognitoError, get_user_friendly_error_message
from common.core.logging_service import get_logger

config_service = ConfigService()


logger = get_logger(__name__)


class CognitoService:
    """Service for handling Cognito authentication operations"""

    def __init__(self) -> None:
        # Use Any for boto3 client to avoid complex type issues
        self.client: Any = None  # Will be initialized lazily when needed
        self.config: dict[str, Any] = config_service.get_cognito_config()
        self.aws_config: dict[str, Any] = config_service.get_aws_credentials()
        self.is_localstack: bool = config_service.is_localstack_enabled()

        # Don't initialize client in __init__ to avoid sync/async issues
        # Client will be initialized lazily when first needed

    def _ensure_client(self) -> None:
        """Ensure the Cognito client is initialized (lazy initialization)"""
        if self.client is not None:
            return

        try:
            # Use default AWS credential chain if no explicit credentials provided
            if self.aws_config["access_key_id"] and self.aws_config["secret_access_key"]:
                session = boto3.Session(
                    aws_access_key_id=self.aws_config["access_key_id"],
                    aws_secret_access_key=self.aws_config["secret_access_key"],
                    region_name=self.config["region"],
                )
            else:
                # Let boto3 use default credential chain (env vars, profile, IAM role)
                session = boto3.Session(region_name=self.config["region"])

            # Use LocalStack endpoint if enabled
            if self.is_localstack and self.config["endpoint_url"]:
                self.client = session.client(  # type: ignore[assignment]
                    "cognito-idp",
                    endpoint_url=self.config["endpoint_url"],
                )
                logger.info("Initialized Cognito client with LocalStack endpoint")
            else:
                self.client = session.client("cognito-idp")  # type: ignore[assignment]
                logger.info("Initialized Cognito client with AWS endpoint")

        except Exception:
            logger.exception("Failed to initialize Cognito client")
            raise

    def _calculate_secret_hash(self, username: str) -> str:
        """Calculate the secret hash for Cognito client"""
        if not self.config["client_secret"]:
            return ""

        message = username + self.config["client_id"]
        dig = hmac.new(
            self.config["client_secret"].encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(dig).decode()

    async def sign_up(
        self,
        email: str,
        password: str,
        full_name: str = "",
        first_name: str = "",
        last_name: str = "",
    ) -> dict[str, Any]:
        """Sign up a new user using email as username with required Cognito attributes"""
        self._ensure_client()
        try:
            # Use email directly as username since Cognito is configured with username-attributes email
            cognito_username = email

            # Required attributes for Cognito (email, family_name, given_name, name)
            user_attributes = [
                {"Name": "email", "Value": email},
            ]

            # Add name attribute (required)
            if full_name:
                user_attributes.append({"Name": "name", "Value": full_name})
            elif first_name and last_name:
                user_attributes.append({"Name": "name", "Value": f"{first_name} {last_name}"})

            # Add given_name (first name) - required by Cognito
            if first_name:
                user_attributes.append({"Name": "given_name", "Value": first_name})
            elif full_name:
                # Extract first name from full name
                first_part = full_name.split()[0] if full_name.split() else ""
                if first_part:
                    user_attributes.append({"Name": "given_name", "Value": first_part})

            # Add family_name (last name) - required by Cognito
            if last_name:
                user_attributes.append({"Name": "family_name", "Value": last_name})
            elif full_name:
                # Extract last name from full name
                parts = full_name.split()
                last_part = parts[-1] if len(parts) > 1 else ""
                if last_part:
                    user_attributes.append({"Name": "family_name", "Value": last_part})

            params = {
                "ClientId": self.config["client_id"],
                "Username": cognito_username,
                "Password": password,
                "UserAttributes": user_attributes,
            }

            # Add secret hash if client secret is configured
            if self.config["client_secret"]:
                params["SecretHash"] = self._calculate_secret_hash(cognito_username)

            response: dict[str, Any] = self.client.sign_up(**params)

            # In development mode, auto-confirm the user
            user_confirmed: bool = response.get("UserConfirmed", False)
            if not user_confirmed and config_service.is_development():
                try:
                    # Auto-confirm user in development
                    await self._admin_confirm_sign_up(email)
                    user_confirmed = True
                    logger.debug(f"User {email} auto-confirmed in development mode")
                except Exception as e:
                    logger.warning(f"Failed to auto-confirm user {email}: {e}")

            logger.debug(f"User {email} signed up successfully")
            return {
                "user_sub": response["UserSub"],
                "user_confirmed": user_confirmed,
                "email": email,
                "cognito_username": cognito_username,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.exception(f"Sign up failed for {email}: {error_code} - {error_message}")
            user_friendly_message = get_user_friendly_error_message(error_code, error_message)
            raise CognitoError(user_friendly_message, error_code=error_code) from e

    async def _admin_confirm_sign_up(self, email: str) -> None:
        """Admin confirm sign up for development mode"""
        self._ensure_client()
        try:
            self.client.admin_confirm_sign_up(
                UserPoolId=self.config["user_pool_id"],
                Username=email,
            )
            logger.debug(f"Admin confirmed user {email}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.exception(f"Admin confirm failed for {email}: {error_code} - {error_message}")
            user_friendly_message = get_user_friendly_error_message(error_code, error_message)
            raise CognitoError(user_friendly_message, error_code=error_code) from e

    async def confirm_sign_up(self, email: str, confirmation_code: str) -> bool:
        """Confirm user sign up with confirmation code"""
        self._ensure_client()
        try:
            # Use email directly as username since Cognito is configured with username-attributes email
            cognito_username = email

            params = {
                "ClientId": self.config["client_id"],
                "Username": cognito_username,
                "ConfirmationCode": confirmation_code,
            }

            if self.config["client_secret"]:
                params["SecretHash"] = self._calculate_secret_hash(cognito_username)

            self.client.confirm_sign_up(**params)
            logger.debug(f"User {email} confirmed successfully")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.exception(f"Confirmation failed for {email}: {error_code} - {error_message}")
            user_friendly_message = get_user_friendly_error_message(error_code, error_message)
            raise CognitoError(user_friendly_message, error_code=error_code) from e

    async def sign_in(self, email: str, password: str) -> dict[str, Any]:
        """Sign in a user and return tokens"""
        self._ensure_client()
        try:
            # Use email directly as username since Cognito is configured with username-attributes email
            cognito_username = email

            logger.debug(f"Attempting sign-in for user: {email}")

            # Use standard USER_PASSWORD_AUTH (no admin auth attempt)
            params = {
                "ClientId": self.config["client_id"],
                "AuthFlow": "USER_PASSWORD_AUTH",
                "AuthParameters": {
                    "USERNAME": cognito_username,
                    "PASSWORD": password,
                },
            }

            if self.config["client_secret"]:
                auth_params = params["AuthParameters"]
                assert isinstance(auth_params, dict)
                auth_params["SECRET_HASH"] = self._calculate_secret_hash(cognito_username)

            response: dict[str, Any] = self.client.initiate_auth(**params)

            auth_result: dict[str, Any] = response["AuthenticationResult"]
            logger.debug(f"User {email} signed in successfully")

            return {
                "access_token": auth_result["AccessToken"],
                "id_token": auth_result["IdToken"],
                "refresh_token": auth_result.get("RefreshToken"),
                "expires_in": auth_result.get("ExpiresIn", 3600),
                "email": email,
                "cognito_username": cognito_username,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.exception(f"Sign in failed for {email}: {error_code} - {error_message}")
            user_friendly_message = get_user_friendly_error_message(error_code, error_message)
            raise CognitoError(user_friendly_message, error_code=error_code) from e

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from access token"""
        self._ensure_client()
        try:
            response: dict[str, Any] = self.client.get_user(AccessToken=access_token)

            user_attributes: dict[str, str] = {}
            for attr in response["UserAttributes"]:
                user_attributes[attr["Name"]] = attr["Value"]

            return {
                "username": response["Username"],
                "user_sub": user_attributes.get("sub"),
                "email": user_attributes.get("email"),
                "name": user_attributes.get("name", ""),
                "email_verified": user_attributes.get("email_verified") == "true",
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.exception(f"Cognito get_user failed with error: {error_code}")
            raise CognitoError(get_user_friendly_error_message(error_code)) from e
        except Exception as e:
            logger.exception("Failed to get user info")
            raise CognitoError("Failed to get user information") from e

    async def user_exists(self, email: str) -> bool:
        """Check if user exists in Cognito"""
        self._ensure_client()
        try:
            # Use email directly as username since Cognito is configured with username-attributes email
            cognito_username = email

            params = {
                "UserPoolId": self.config["user_pool_id"],
                "Username": cognito_username,
            }

            self.client.admin_get_user(**params)
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "UserNotFoundException":
                return False
            else:
                logger.exception(f"Cognito admin_get_user failed with error: {error_code}")
                raise CognitoError(get_user_friendly_error_message(error_code)) from e
        except Exception as e:
            logger.exception("Failed to check if user exists")
            raise CognitoError("Failed to check user existence") from e

    async def refresh_token(self, refresh_token: str, email: str) -> dict[str, Any]:
        """Refresh access token using refresh token"""
        self._ensure_client()
        try:
            # Use email directly as username since Cognito is configured with username-attributes email
            cognito_username = email

            params = {
                "ClientId": self.config["client_id"],
                "AuthFlow": "REFRESH_TOKEN_AUTH",
                "AuthParameters": {
                    "REFRESH_TOKEN": refresh_token,
                },
            }

            if self.config["client_secret"]:
                auth_params = params["AuthParameters"]
                assert isinstance(auth_params, dict)
                auth_params["SECRET_HASH"] = self._calculate_secret_hash(cognito_username)

            response: dict[str, Any] = self.client.initiate_auth(**params)

            auth_result: dict[str, Any] = response["AuthenticationResult"]
            logger.debug(f"Token refreshed successfully for {email}")

            return {
                "access_token": auth_result["AccessToken"],
                "id_token": auth_result["IdToken"],
                "expires_in": auth_result.get("ExpiresIn", 7200),  # Default to 2 hours
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.exception(f"Token refresh failed: {error_code} - {error_message}")
            user_friendly_message = get_user_friendly_error_message(error_code, error_message)
            raise CognitoError(user_friendly_message, error_code=error_code) from e

    async def get_user_info_from_oauth_token(self, id_token: str) -> dict[str, Any]:
        """Get user information from OAuth ID token (JWT)"""
        try:
            # Decode JWT token (ID token contains user info)
            # JWT format: header.payload.signature
            parts = id_token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT token format")

            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            payload += "=" * (4 - len(payload) % 4)
            decoded_payload = base64.urlsafe_b64decode(payload)
            user_data: dict[str, Any] = json.loads(decoded_payload.decode("utf-8"))

            logger.debug(f"Decoded OAuth user data: {user_data}")

            return {
                "username": user_data.get("email", ""),  # Use email as username
                "user_sub": user_data.get("sub", ""),
                "email": user_data.get("email", ""),
                "name": user_data.get("name", ""),
                "given_name": user_data.get("given_name", ""),
                "family_name": user_data.get("family_name", ""),
                "email_verified": user_data.get("email_verified", False),
            }

        except Exception:
            logger.exception("Failed to decode OAuth ID token")
            raise CognitoError("Failed to extract user information from OAuth token") from None

    def generate_oauth_url(self, state: str) -> str:
        """Generate OAuth URL for Google social login via Cognito"""
        try:
            # Use custom domain if configured, otherwise use default Cognito domain
            domain = self.config["domain"]
            base_url = domain if domain.startswith("http") else f"https://{domain}.auth.{self.config['region']}.amazoncognito.com"

            # URL encode the parameters
            params = {
                "client_id": self.config["client_id"],
                "response_type": "code",
                "scope": "openid email profile",  # Full scopes including profile
                "redirect_uri": self.config["callback_url"],
                "identity_provider": "Google",
                "state": state,
            }

            query_string = urllib.parse.urlencode(params)
            oauth_url = f"{base_url}/oauth2/authorize?{query_string}"

            logger.debug(f"Generated OAuth URL: {oauth_url}")
            return oauth_url
        except Exception:
            logger.exception("Failed to generate OAuth URL")
            raise CognitoError("Failed to generate OAuth URL") from None

    async def exchange_oauth_code(self, code: str) -> dict[str, Any]:
        """Exchange OAuth authorization code for tokens"""
        try:
            # Prepare token exchange request
            domain = self.config["domain"]
            token_url = (
                f"{domain}/oauth2/token" if domain.startswith("http") else f"https://{domain}.auth.{self.config['region']}.amazoncognito.com/oauth2/token"
            )

            data = {
                "grant_type": "authorization_code",
                "client_id": self.config["client_id"],
                "code": code,
                "redirect_uri": self.config["callback_url"],
            }

            # Add client secret if configured
            if self.config["client_secret"]:
                data["client_secret"] = self.config["client_secret"]

            # Make async HTTP request
            logger.debug(f"Making token exchange request to: {token_url}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                _ = response.raise_for_status()
                result: dict[str, Any] = response.json()

                logger.debug("OAuth code exchange successful")
                return {
                    "access_token": result["access_token"],
                    "id_token": result["id_token"],
                    "refresh_token": result.get("refresh_token"),
                    "expires_in": result.get("expires_in", 7200),  # Default to 2 hours
                }

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.exception(f"OAuth token exchange HTTP error {e.response.status_code}: {error_body}")
            raise CognitoError(f"OAuth token exchange failed: {e.response.status_code} - {error_body}") from e
        except Exception:
            logger.exception("OAuth code exchange failed")
            raise CognitoError("Failed to exchange OAuth code for tokens") from None

    async def change_password(self, email: str, old_password: str, new_password: str) -> bool:
        """Change user password using Cognito"""
        self._ensure_client()
        try:
            # Use email directly as username since Cognito is configured with username-attributes email
            cognito_username = email

            # First, verify the old password by attempting to sign in
            try:
                _ = await self.sign_in(email, old_password)
            except CognitoError as e:
                raise CognitoError("Current password is incorrect", error_code="NotAuthorizedException") from e

            # Use admin_set_user_password to change the password
            # This is more reliable as it doesn't require the user to be signed in
            params = {
                "UserPoolId": self.config["user_pool_id"],
                "Username": cognito_username,
                "Password": new_password,
                "Permanent": True,  # Make this a permanent password change
            }

            self.client.admin_set_user_password(**params)
            logger.info(f"Password changed successfully for user {email}")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.exception(f"Password change failed for {email}: {error_code} - {error_message}")

            # Map Cognito errors to user-friendly messages
            if error_code == "InvalidParameterException":
                if "password did not conform with policy" in error_message:
                    raise CognitoError(
                        "New password does not meet requirements. Password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters.",
                        error_code=error_code,
                    ) from e
                if "password cannot be the same as the old password" in error_message:
                    raise CognitoError("New password cannot be the same as the old password.", error_code=error_code) from e
            elif error_code == "NotAuthorizedException":
                raise CognitoError("Current password is incorrect", error_code=error_code) from e
            elif error_code == "UserNotFoundException":
                raise CognitoError("User not found", error_code=error_code) from e

            user_friendly_message = get_user_friendly_error_message(error_code, error_message)
            raise CognitoError(user_friendly_message, error_code=error_code) from e
        except CognitoError:
            # Re-raise Cognito errors as-is
            raise
        except Exception as e:
            logger.exception("Unexpected error during password change", email=email)
            raise CognitoError("Failed to change password") from e

    async def delete_user(self, email: str) -> bool:
        """Delete user from Cognito"""
        self._ensure_client()
        try:
            # Use email directly as username since Cognito is configured with username-attributes email
            cognito_username = email

            params = {
                "UserPoolId": self.config["user_pool_id"],
                "Username": cognito_username,
            }

            self.client.admin_delete_user(**params)
            logger.info(f"User {email} deleted successfully from Cognito")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.exception(f"User deletion failed for {email}: {error_code} - {error_message}")

            if error_code == "UserNotFoundException":
                raise CognitoError("User not found", error_code=error_code) from e

            user_friendly_message = get_user_friendly_error_message(error_code, error_message)
            raise CognitoError(user_friendly_message, error_code=error_code) from e
        except Exception as e:
            logger.exception("Unexpected error during user deletion", email=email)
            raise CognitoError("Failed to delete user") from e


# Note: No global instance - use service factory to get appropriate service (mock or real)
