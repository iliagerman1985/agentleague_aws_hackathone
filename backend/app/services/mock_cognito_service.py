"""Mock Cognito service for testing purposes.
Provides the same interface as the real Cognito service but checks the database for users.
"""

import hashlib
import logging
import time
from typing import Any

from common.core.exceptions import CognitoError
from shared_db.crud.user import UserDAO
from shared_db.db import AsyncSessionLocal

logger = logging.getLogger(__name__)


class MockCognitoService:
    """Mock implementation of Cognito service for testing.
    Checks database for users and generates deterministic user_sub values.
    """

    def __init__(self) -> None:
        # Only store tokens in memory, users are in database
        self._tokens: dict[str, dict[str, Any]] = {}
        self._user_dao = UserDAO()
        logger.info("Initialized Mock Cognito Service")

    def _generate_user_sub(self, email: str) -> str:
        """Generate deterministic user_sub based on email"""
        email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
        return f"mock-user-{email_hash}"

    async def sign_up(self, email: str, password: str, full_name: str = "", first_name: str = "", last_name: str = "") -> dict[str, Any]:
        """Sign up a new user using email as username"""
        try:
            # Generate deterministic user_sub
            user_sub = self._generate_user_sub(email)

            # For mock service, we'll just return success
            # In real implementation, this would create the user in Cognito
            # The actual user creation in database is handled by the signup endpoint

            logger.info(f"Mock Cognito: Created user {email} with sub {user_sub}")

            return {
                "user_sub": user_sub,
                "user_confirmed": True,
                "email": email,
                "cognito_username": email,
            }

        except Exception as e:
            logger.exception(f"Mock Cognito sign up failed for {email}")
            raise CognitoError(f"Sign up failed: {e!s}") from e

    async def sign_in(self, email: str, password: str) -> dict[str, Any]:
        """Sign in a user and return mock tokens"""
        try:
            # Check database for user via DAO
            async with AsyncSessionLocal() as db:
                user = await self._user_dao.get_by_email(db, email)
                if not user:
                    logger.error(f"Mock Cognito: User {email} not found in database")
                    raise CognitoError("User not found")

                # For mock service, we'll use a simple password check
                # In real implementation, passwords would be hashed
                # For testing, we'll check against known test passwords or accept common test passwords
                test_passwords = {
                    "admin@admin.com": "Cowabunga2@",
                    "user@test.com": "TestPassword123!",
                    "test@example.com": "TestPassword123!",
                }

                expected_password = test_passwords.get(email)

                # If not a predefined test user, accept common test passwords
                if not expected_password:
                    common_test_passwords = ["TestPassword123!", "Password123!", "Test123!"]
                    if password not in common_test_passwords:
                        logger.error(f"Mock Cognito: Invalid password for {email}")
                        raise CognitoError("Invalid credentials")
                elif password != expected_password:
                    logger.error(f"Mock Cognito: Invalid password for {email}")
                    raise CognitoError("Invalid credentials")

                # Generate mock tokens
                timestamp = int(time.time())
                access_token = f"mock-access-{user.cognito_sub}-{timestamp}"
                id_token = f"mock-id-{user.cognito_sub}-{timestamp}"
                refresh_token = f"mock-refresh-{user.cognito_sub}"

                # Store tokens for validation (2 hours = 7200 seconds)
                self._tokens[access_token] = {
                    "user_sub": user.cognito_sub,
                    "email": email,
                    "token_type": "access",
                    "expires_at": timestamp + 7200,
                }
                self._tokens[id_token] = {
                    "user_sub": user.cognito_sub,
                    "email": email,
                    "token_type": "id",
                    "expires_at": timestamp + 7200,
                }

                logger.info(f"Mock Cognito: User {email} signed in successfully")

                return {
                    "access_token": access_token,
                    "id_token": id_token,
                    "refresh_token": refresh_token,
                    "expires_in": 7200,  # 2 hours
                    "token_type": "Bearer",
                    "email": email,
                    "cognito_username": email,
                }

        except Exception as e:
            logger.exception(f"Mock Cognito sign in failed for {email}")
            raise CognitoError(f"Sign in failed: {e!s}") from e

    async def refresh_token(self, refresh_token: str, email: str) -> dict[str, Any]:
        """Refresh tokens for a user"""
        try:
            # Find user in database via DAO
            async with AsyncSessionLocal() as db:
                user = await self._user_dao.get_by_email(db, email)
                if not user:
                    raise CognitoError("User not found")

                # Generate new tokens
                timestamp = int(time.time())
                access_token = f"mock-access-{user.cognito_sub}-{timestamp}"
                id_token = f"mock-id-{user.cognito_sub}-{timestamp}"

                # Store new tokens (2 hours = 7200 seconds)
                self._tokens[access_token] = {
                    "user_sub": user.cognito_sub,
                    "email": email,
                    "token_type": "access",
                    "expires_at": timestamp + 7200,
                }
                self._tokens[id_token] = {
                    "user_sub": user.cognito_sub,
                    "email": email,
                    "token_type": "id",
                    "expires_at": timestamp + 7200,
                }

                logger.info(f"Mock Cognito: Token refreshed for {email}")

                return {
                    "access_token": access_token,
                    "id_token": id_token,
                    "expires_in": 7200,  # 2 hours
                }

        except Exception as e:
            logger.exception(f"Mock Cognito token refresh failed for {email}")
            raise CognitoError(f"Token refresh failed: {e!s}") from e

    async def user_exists(self, email: str) -> bool:
        """Check if user exists"""
        async with AsyncSessionLocal() as db:
            user = await self._user_dao.get_by_email(db, email)
            return user is not None

    async def get_user_by_email(self, email: str) -> dict[str, Any]:
        """Get user data by email"""
        async with AsyncSessionLocal() as db:
            user = await self._user_dao.get_by_email(db, email)
            if user:
                return {
                    "user_sub": user.cognito_sub,
                    "email": user.email,
                    "full_name": user.full_name,
                    "cognito_username": user.email,
                }
            return {}

    def validate_token(self, token: str) -> dict[str, Any]:
        """Validate a token and return token data"""
        if token in self._tokens:
            token_data = self._tokens[token]
            # Check if token is expired
            if token_data["expires_at"] > int(time.time()):
                return token_data
            else:
                logger.warning(f"Mock Cognito: Token {token[:20]}... has expired")
                raise Exception("Token expired")
        else:
            logger.warning(f"Mock Cognito: Invalid token {token[:20]}...")
            raise Exception("Invalid token")

    async def confirm_sign_up(self, email: str, confirmation_code: str) -> None:
        """Confirm user sign up (mock implementation - always succeeds)"""
        # For mock service, we just log the confirmation
        # In real implementation, this would confirm the user in Cognito
        logger.info(f"Mock Cognito: Confirmed user {email} with code {confirmation_code}")

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user info from access token"""
        try:
            token_data = self.validate_token(access_token)
            email = token_data["email"]

            async with AsyncSessionLocal() as db:
                user = await self._user_dao.get_by_email(db, email)
                if user:
                    return {
                        "user_sub": user.cognito_sub,
                        "email": user.email,
                        "name": user.full_name,  # Use 'name' to match real Cognito response
                        "full_name": user.full_name,  # Keep both for compatibility
                        "cognito_username": user.email,
                    }
                else:
                    raise CognitoError("User not found")

        except Exception as e:
            logger.exception("Mock Cognito: Failed to get user info")
            raise CognitoError("Failed to get user info") from e

    def generate_oauth_url(self, state: str) -> str:
        """Generate mock OAuth URL for testing"""
        # For mock service, return a fake OAuth URL
        callback_url = "http://localhost:5173/auth/callback"
        mock_url = f"http://mock-oauth.example.com/authorize?state={state}&redirect_uri={callback_url}"
        logger.info(f"Mock Cognito: Generated OAuth URL: {mock_url}")
        return mock_url

    async def exchange_oauth_code(self, code: str) -> dict[str, Any]:
        """Mock OAuth code exchange - returns fake tokens"""
        try:
            # For mock service, generate fake tokens
            timestamp = int(time.time())
            access_token = f"mock-oauth-access-{timestamp}"
            id_token = f"mock-oauth-id-{timestamp}"
            refresh_token = f"mock-oauth-refresh-{timestamp}"

            logger.info("Mock Cognito: OAuth code exchange successful")
            return {
                "access_token": access_token,
                "id_token": id_token,
                "refresh_token": refresh_token,
                "expires_in": 7200,  # 2 hours
            }
        except Exception as e:
            logger.exception("Mock Cognito: OAuth code exchange failed")
            raise Exception("Failed to exchange OAuth code for tokens") from e

    async def get_user_info_from_oauth_token(self, id_token: str) -> dict[str, Any]:
        """Mock OAuth user info extraction from ID token"""
        try:
            # For mock service, return fake user data
            # In a real test, you might want to customize this based on the test scenario
            mock_user_data = {
                "username": "test@example.com",
                "user_sub": "mock-oauth-user-12345",
                "email": "test@example.com",
                "name": "Test User",
                "given_name": "Test",
                "family_name": "User",
                "email_verified": True,
            }

            logger.info(f"Mock Cognito: Extracted OAuth user data: {mock_user_data}")
            return mock_user_data

        except Exception as e:
            logger.exception("Mock Cognito: Failed to extract OAuth user info")
            raise Exception("Failed to extract user information from OAuth token") from e

    async def change_password(self, email: str, old_password: str, new_password: str) -> bool:
        """Change user password (mock implementation)"""
        try:
            # Verify old password first
            try:
                _ = await self.sign_in(email, old_password)
            except CognitoError:
                raise CognitoError("Current password is incorrect", error_code="NotAuthorizedException")

            # Basic password validation for mock service
            if len(new_password) < 8:
                raise CognitoError(
                    "New password does not meet requirements. Password must be at least 8 characters long.", error_code="InvalidParameterException"
                )

            # Check if new password is different from old password
            if new_password == old_password:
                raise CognitoError("New password cannot be the same as the old password.", error_code="InvalidParameterException")

            # For mock service, we just log the password change
            # In a real implementation, this would update the password in Cognito
            logger.info(f"Mock Cognito: Password changed successfully for user {email}")
            return True

        except CognitoError:
            # Re-raise Cognito errors as-is
            raise
        except Exception as e:
            logger.exception(f"Mock Cognito: Unexpected error during password change for {email}: {e}")
            raise CognitoError("Failed to change password") from e

    async def delete_user(self, email: str) -> bool:
        """Delete user from mock Cognito"""
        try:
            # For mock service, we just log the deletion
            # In a real implementation, this would delete the user from Cognito
            # The actual user deletion from database is handled by the delete-account endpoint

            # Check if user exists by trying to sign in
            try:
                _ = await self.get_user_info_from_email(email)
            except CognitoError:
                raise CognitoError("User not found", error_code="UserNotFoundException")

            # Remove any stored tokens for this user
            user_sub = self._generate_user_sub(email)
            _ = self._tokens.pop(user_sub, None)

            logger.info(f"Mock Cognito: User {email} deleted successfully")
            return True

        except CognitoError:
            # Re-raise Cognito errors as-is
            raise
        except Exception as e:
            logger.exception(f"Mock Cognito: Unexpected error during user deletion for {email}: {e}")
            raise CognitoError("Failed to delete user") from e

    async def get_user_info_from_email(self, email: str) -> dict[str, Any]:
        """Get user info by email (helper method for mock service)"""
        user_sub = self._generate_user_sub(email)

        # Check if user exists in our token storage
        if user_sub not in self._tokens:
            raise CognitoError("User not found", error_code="UserNotFoundException")

        return {
            "username": email,
            "user_sub": user_sub,
            "email": email,
            "name": "",  # Would be populated from database in real implementation
            "email_verified": True,
        }

    def clear_all_users(self) -> None:
        """Clear all users and tokens (for testing)"""
        # Only clear tokens, users are in database
        self._tokens.clear()
        logger.info("Mock Cognito: Cleared all tokens")


# Note: No global instance - use service factory to get appropriate service
