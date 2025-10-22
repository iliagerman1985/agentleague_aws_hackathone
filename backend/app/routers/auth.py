"""Authentication router for user registration, login, and token management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_avatar_service,
    get_cognito_service_dependency,
    get_current_active_user,
    get_db,
    get_llm_integration_service,
    get_user_service,
)
from app.services.avatar_service import AvatarService
from app.services.cognito_service import CognitoService
from app.services.llm_integration_service import LLMIntegrationService
from app.services.mock_cognito_service import MockCognitoService
from app.services.user_service import UserService
from app.utils.username_utils import validate_and_normalize_email
from common.core.exceptions import CognitoError
from common.core.logging_service import get_logger
from shared_db.models.user import AvatarType
from shared_db.schemas.auth import (
    ConfirmSignUpRequest,
    ConfirmSignUpResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
    MessageResponse,
    OAuthCallbackRequest,
    OAuthUrlResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    SignInRequest,
    SignInResponse,
    SignUpRequest,
    SignUpResponse,
    UserInfo,
)
from shared_db.schemas.user import UserResponse, UserUpdate

logger = get_logger(__name__)

auth_router = APIRouter()


@auth_router.post("/signup", response_model=SignUpResponse)
async def sign_up(
    request: SignUpRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
):
    """Register a new user with Cognito and create user record in database."""
    try:
        # Validate password confirmation
        if request.password != request.password_confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match",
            )

        # Validate and normalize email
        try:
            normalized_email = validate_and_normalize_email(request.email)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

        # Check if user already exists in database
        existing_email = await user_service.get_user_by_email(db, normalized_email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Combine first and last names to create full name
        full_name = f"{request.first_name} {request.last_name}".strip()

        # Sign up user with Cognito
        cognito_response = await cognito_service.sign_up(
            email=normalized_email,
            password=request.password,
            full_name=full_name,
            first_name=request.first_name,
            last_name=request.last_name,
        )

        # Create user record in database (only store full_name, not given_name or picture)
        user = await user_service.create_user_from_params(
            db=db,
            username=normalized_email,  # Use email as username
            email=normalized_email,
            full_name=full_name,
            cognito_sub=cognito_response["user_sub"],
        )

        # Create system LLM integrations for the new user
        if user:
            try:
                _ = await llm_integration_service.create_system_integrations_for_user(db, user.id)
                logger.info(f"Created system LLM integrations for new user {user.email}")
            except Exception as e:
                logger.warning(f"Failed to create LLM integrations for new user {user.email}: {e}")
                # Don't fail the signup if integration creation fails

        logger.info(f"User {normalized_email} signed up successfully")

        # Determine the message based on whether user is confirmed
        if cognito_response["user_confirmed"]:
            message = "User registered and confirmed successfully. You can now sign in."
        else:
            message = "User registered successfully. Please check your email for confirmation code."

        return SignUpResponse(
            message=message,
            user_sub=cognito_response["user_sub"],
            user_confirmed=cognito_response["user_confirmed"],
        )

    except HTTPException:
        raise
    except CognitoError as e:
        logger.exception(f"Cognito error during sign up for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error during sign up for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from e


@auth_router.post("/confirm-signup", response_model=ConfirmSignUpResponse)
async def confirm_sign_up(
    request: ConfirmSignUpRequest,
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
):
    """Confirm user sign up with confirmation code."""
    try:
        _ = await cognito_service.confirm_sign_up(
            email=request.email,
            confirmation_code=request.confirmation_code,
        )

        logger.debug(f"User {request.email} confirmed successfully")

        return ConfirmSignUpResponse(
            message="User confirmed successfully. You can now sign in.",
        )

    except CognitoError as e:
        logger.exception(f"Cognito error during confirmation for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error during confirmation for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from e


@auth_router.post("/signin", response_model=SignInResponse)
async def sign_in(
    request: SignInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
):
    """Sign in user and return access tokens."""
    try:
        # Authenticate with Cognito
        tokens = await cognito_service.sign_in(
            email=request.email,
            password=request.password,
        )

        # Get user info from Cognito
        user_info = await cognito_service.get_user_info(tokens["access_token"])

        # Get or update user in database
        user = await user_service.get_user_by_cognito_sub(db, user_info["user_sub"])
        if not user:
            # User might exist with email but no cognito_sub
            user = await user_service.get_user_by_email(db, request.email)
            if user:
                # Update user with cognito_sub
                user_update = UserUpdate(cognito_sub=user_info["user_sub"])
                user = await user_service.update_user(db, user.id, user_update)
            else:
                # Create new user record
                user = await user_service.create_user_from_params(
                    db=db,
                    username=request.email,  # Use email as username
                    email=user_info["email"],
                    full_name=user_info["name"],
                    cognito_sub=user_info["user_sub"],
                )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve user",
            )

        logger.debug(f"User {request.email} signed in successfully")

        return SignInResponse(
            access_token=tokens["access_token"],
            id_token=tokens["id_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens["expires_in"],
            user=UserInfo(
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                nickname=getattr(user, "nickname", None),
                display_name=getattr(user, "display_name", None),
                role=user.role,
                is_active=user.is_active,
                coins_balance=user.coins_balance,
                user_sub=user.cognito_sub,
            ),
        )

    except CognitoError as e:
        logger.exception(f"Cognito error during sign in for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error during sign in for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from e


@auth_router.post("/refresh-token", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
):
    """Refresh access token using refresh token."""
    try:
        tokens = await cognito_service.refresh_token(
            refresh_token=request.refresh_token,
            email=request.email,
        )

        logger.info(f"Token refreshed successfully for {request.email}")

        return RefreshTokenResponse(
            access_token=tokens["access_token"],
            id_token=tokens["id_token"],
            expires_in=tokens["expires_in"],
        )

    except Exception as e:
        logger.exception(f"Token refresh failed for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed",
        ) from e


@auth_router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: Annotated[UserResponse, Depends(get_current_active_user)]):
    """Get current user information."""
    # Compute display_name with proper fallback: nickname → full_name → username
    display_name = getattr(current_user, "nickname", None) or current_user.full_name or current_user.username
    return UserInfo(
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        nickname=getattr(current_user, "nickname", None),
        display_name=display_name,
        role=current_user.role,
        is_active=current_user.is_active,
        coins_balance=current_user.coins_balance,
        user_sub=current_user.cognito_sub,
        avatar_url=current_user.avatar_url,
        avatar_type=current_user.avatar_type,
    )


@auth_router.put("/me", response_model=UserInfo)
async def update_current_user_info(
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Update current user's profile (nickname, full_name, avatar metadata, etc.)."""
    try:
        updated = await user_service.update_user(db, current_user.id, user_update)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return UserInfo(
            username=updated.username,
            email=updated.email,
            full_name=updated.full_name,
            nickname=getattr(updated, "nickname", None),
            display_name=getattr(updated, "display_name", None),
            role=updated.role,
            is_active=updated.is_active,
            coins_balance=updated.coins_balance,
            user_sub=updated.cognito_sub,
            avatar_url=updated.avatar_url,
            avatar_type=updated.avatar_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update current user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user") from e


@auth_router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
):
    """Change user password."""
    try:
        _ = await cognito_service.change_password(
            email=current_user.email,
            old_password=request.old_password,
            new_password=request.new_password,
        )

        logger.info(f"Password changed successfully for user {current_user.email}")

        return MessageResponse(
            message="Password changed successfully.",
        )

    except CognitoError as e:
        logger.exception(f"Cognito error during password change for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error during password change for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from e


@auth_router.post("/signout", response_model=MessageResponse)
async def sign_out():
    """Sign out user (client should discard tokens)."""
    return MessageResponse(
        message="Signed out successfully. Please discard your tokens.",
    )


@auth_router.delete("/delete-account", response_model=DeleteAccountResponse)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
):
    """Delete user account and all related data."""
    try:
        # Verify password before allowing deletion
        try:
            _ = await cognito_service.sign_in(current_user.email, request.password)
        except CognitoError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        # Delete user from Cognito first
        _ = await cognito_service.delete_user(current_user.email)

        # Delete user from database with cascading
        db_deleted = await user_service.delete_user_with_cascade(db, current_user.id)

        if not db_deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user data",
            )

        logger.info(f"Account deleted successfully for user {current_user.email}")

        return DeleteAccountResponse(
            message="Account deleted successfully. All your data has been removed.",
            success=True,
        )

    except CognitoError as e:
        logger.exception(f"Cognito error during account deletion for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during account deletion for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from e


@auth_router.get("/oauth/google/url", response_model=OAuthUrlResponse)
async def get_google_oauth_url(
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
):
    """Generate Google OAuth URL for social login."""
    try:
        import secrets

        # Generate a secure random state for CSRF protection
        state = secrets.token_urlsafe(32)

        oauth_url = cognito_service.generate_oauth_url(state)

        logger.info("Generated Google OAuth URL")

        return OAuthUrlResponse(
            oauth_url=oauth_url,
            state=state,
        )

    except Exception as e:
        logger.exception(f"Failed to generate OAuth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate OAuth URL",
        ) from e


@auth_router.post("/oauth/callback", response_model=SignInResponse)
async def oauth_callback(
    request: OAuthCallbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    cognito_service: Annotated[CognitoService | MockCognitoService, Depends(get_cognito_service_dependency)],
    avatar_service: Annotated[AvatarService, Depends(get_avatar_service)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
):
    """Handle OAuth callback and sign in user."""
    try:
        # Exchange authorization code for tokens
        tokens = await cognito_service.exchange_oauth_code(request.code)

        # Get user info from ID token (for OAuth, use ID token instead of access token)
        user_info = await cognito_service.get_user_info_from_oauth_token(tokens["id_token"])

        # Get or create user in database
        user = await user_service.get_user_by_cognito_sub(db, user_info["user_sub"])
        if not user:
            # Check if user exists by email
            user = await user_service.get_user_by_email(db, user_info["email"])
            if user:
                # Update existing user with cognito_sub and potentially avatar
                user_update = UserUpdate(cognito_sub=user_info["user_sub"])

                # Process avatar if this is a Google login and user doesn't have an avatar yet
                picture_url = user_info.get("picture")
                if picture_url and (not user.avatar_url or user.avatar_type == AvatarType.DEFAULT):
                    try:
                        avatar_url, avatar_type = await avatar_service.process_url_avatar(picture_url)
                        user_update.avatar_url = avatar_url
                        user_update.avatar_type = avatar_type
                        logger.info(f"Updated avatar for user {user.email} from Google profile")
                    except Exception as e:
                        logger.warning(f"Failed to process Google avatar for {user.email}: {e}")

                user = await user_service.update_user(db, user.id, user_update)
            else:
                # Create new user from social login
                # Extract first and last names from full name for display
                name_parts = user_info.get("name", "").split()
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                # Process avatar from Google profile picture
                avatar_url = None
                avatar_type = AvatarType.DEFAULT
                picture_url = user_info.get("picture")
                if picture_url:
                    try:
                        avatar_url, avatar_type = await avatar_service.process_url_avatar(picture_url)
                        logger.info(f"Processed avatar for new user {user_info['email']} from Google profile")
                    except Exception as e:
                        logger.warning(f"Failed to process Google avatar for new user {user_info['email']}: {e}")

                user = await user_service.create_user_from_params(
                    db=db,
                    username=user_info["email"],
                    email=user_info["email"],
                    full_name=user_info.get("name", f"{first_name} {last_name}".strip()),
                    cognito_sub=user_info["user_sub"],
                    avatar_url=avatar_url,
                    avatar_type=avatar_type,
                )

                # Create system LLM integrations for the new user
                if user:
                    try:
                        _ = await llm_integration_service.create_system_integrations_for_user(db, user.id)
                        logger.info(f"Created system LLM integrations for new OAuth user {user.email}")
                    except Exception as e:
                        logger.warning(f"Failed to create LLM integrations for new user {user.email}: {e}")
                        # Don't fail the signup if integration creation fails

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve user",
            )

        logger.debug(f"User {user_info['email']} signed in via OAuth")

        # Compute display_name with proper fallback: nickname → full_name → username
        display_name = getattr(user, "nickname", None) or user.full_name or user.username

        return SignInResponse(
            access_token=tokens["access_token"],
            id_token=tokens["id_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens["expires_in"],
            user=UserInfo(
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                nickname=getattr(user, "nickname", None),
                display_name=display_name,
                role=user.role,
                is_active=user.is_active,
                coins_balance=user.coins_balance,
                user_sub=user.cognito_sub,
                avatar_url=user.avatar_url,
                avatar_type=user.avatar_type,
            ),
        )

    except Exception as e:
        logger.exception(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed",
        ) from e
