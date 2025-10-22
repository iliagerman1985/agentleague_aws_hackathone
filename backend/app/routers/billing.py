"""Billing routes for Stripe coin purchases."""

from typing import Annotated, Any, cast

import stripe as stripe_sdk
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_active_user, get_db, get_payment_service, get_stripe_service
from app.schemas.billing import (
    CheckoutSessionCompletedEvent,
    ConfirmableStripeSession,
    ConfirmSessionResponse,
    ConfirmSessionStatus,
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    ListBundlesResponse,
    StripePaymentStatus,
    StripeSessionStatus,
    WebhookResponse,
)
from app.services.payment_service import PaymentService
from app.services.stripe_service import StripeService
from common.utils.tsid import TSID
from common.utils.utils import get_logger
from shared_db.schemas.user import UserResponse

router = APIRouter(prefix="/billing", tags=["billing"])
logger = get_logger()


@router.get("/bundles", response_model=ListBundlesResponse)
async def list_bundles(
    stripe_service: Annotated[StripeService, Depends(get_stripe_service)],
    _current_user: Annotated[UserResponse, Depends(get_current_active_user)],
):
    bundles = stripe_service.get_bundles()
    return ListBundlesResponse(bundles=bundles)


@router.post("/checkout-session", response_model=CreateCheckoutSessionResponse)
async def create_checkout_session(
    req: CreateCheckoutSessionRequest,
    user: Annotated[UserResponse, Depends(get_current_active_user)],
    stripe_service: Annotated[StripeService, Depends(get_stripe_service)],
):
    try:
        result = await stripe_service.create_checkout_session(user, req.bundle_id, req.quantity)
        return CreateCheckoutSessionResponse(checkout_url=result.url, session_id=result.id)
    except Exception as e:
        logger.exception(f"Failed to create checkout session: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_service: Annotated[StripeService, Depends(get_stripe_service)],
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
):
    # Verify signature and parse event
    payload = await request.body()
    wh_secret = stripe_service.webhook_secret

    try:
        event = cast(
            "dict[str, Any]",
            stripe_sdk.Webhook.construct_event(  # pyright: ignore[reportUnknownMemberType]
                payload=payload,
                sig_header=str(stripe_signature or ""),
                secret=wh_secret,
            ),
        )
    except Exception as e:
        logger.exception(f"Stripe webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    # Handle checkout.session.completed
    if event.get("type") == "checkout.session.completed":
        try:
            from common.ids import UserId

            evt = CheckoutSessionCompletedEvent.model_validate(event)
            session_id = evt.data.object.id
            metadata = evt.data.object.metadata
            uid = metadata.user_id
            coins = int(metadata.coins or 0)
            if uid and coins > 0:
                credited, _ = await payment_service.credit_user_once(
                    db,
                    stripe_session_id=session_id,
                    user_id=UserId(TSID.from_string_by_length(uid)),
                    coins=coins,
                )
                if credited:
                    logger.info("Credited coins from Stripe webhook", extra={"user_id": uid, "coins": coins, "session_id": session_id})
                else:
                    logger.info("Duplicate webhook or already credited", extra={"user_id": uid, "session_id": session_id})
            else:
                logger.warning("Stripe session missing metadata for crediting", extra={"metadata": metadata.model_dump()})
        except Exception as e:
            logger.exception(f"Failed to process checkout.session.completed: {e}")

    return WebhookResponse(status="ok")


@router.post("/confirm-session")
async def confirm_session(
    request: Request,
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserResponse, Depends(get_current_active_user)],
) -> ConfirmSessionResponse:
    """Confirm a Stripe checkout session (fallback when webhook isn't available).
    Verifies with Stripe, then idempotently credits coins via the ledger.
    """
    try:
        body = await request.json()
        session_id = str(body.get("session_id", "")).strip()
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        raw = stripe_sdk.checkout.Session.retrieve(session_id)
        sess = ConfirmableStripeSession.model_validate(raw)

        # Normalize enum-or-string values to strings and compare to enum values
        from enum import StrEnum as _StrEnum

        payment_status_val = sess.payment_status.value if isinstance(sess.payment_status, _StrEnum) else str(sess.payment_status)
        status_val = sess.status.value if isinstance(sess.status, _StrEnum) else str(sess.status)

        if payment_status_val != StripePaymentStatus.PAID.value:
            return ConfirmSessionResponse(status=ConfirmSessionStatus.PENDING, coins_added=0)
        if status_val != StripeSessionStatus.COMPLETE.value:
            return ConfirmSessionResponse(status=ConfirmSessionStatus.PENDING, coins_added=0)

        uid = str(sess.metadata.user_id or "")
        coins = int(sess.metadata.coins or 0)
        if not uid or coins <= 0:
            raise HTTPException(status_code=400, detail="Invalid session metadata")

        from common.ids import UserId

        if uid != str(user.id):
            # Do not allow crediting a different user
            raise HTTPException(status_code=403, detail="Session does not belong to this user")

        credited, added = await payment_service.credit_user_once(
            db,
            stripe_session_id=session_id,
            user_id=UserId(TSID.from_string_by_length(uid)),
            coins=coins,
        )
        if credited:
            logger.info("Credited coins via confirm-session", extra={"user_id": uid, "coins": coins, "session_id": session_id})
        else:
            logger.info("Confirm-session duplicate, already credited", extra={"user_id": uid, "session_id": session_id})
        return ConfirmSessionResponse(status=ConfirmSessionStatus.CREDITED if credited else ConfirmSessionStatus.PENDING, coins_added=added)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"confirm-session failed: {e}")
        raise HTTPException(status_code=400, detail="Could not confirm session") from e
