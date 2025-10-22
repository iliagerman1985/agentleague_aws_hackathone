"""Billing-related Pydantic schemas (Stripe)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from common.utils.json_model import JsonModel


class ConfirmSessionStatus(StrEnum):
    """Status values for session confirmation."""

    CREDITED = "credited"
    PENDING = "pending"
    INVALID = "invalid"


class WebhookResponse(JsonModel):
    """Response for Stripe webhook processing."""

    status: str = Field(..., description="Processing status")


class CoinBundle(BaseModel):
    id: str
    name: str
    coins: int
    currency: str
    amount_cents: int
    price_id: str | None = None
    payment_link_url: str | None = None


class ListBundlesResponse(JsonModel):
    bundles: list[CoinBundle]


class CreateCheckoutSessionRequest(BaseModel):
    bundle_id: str = Field(..., description="ID of coin bundle to purchase")
    quantity: int = Field(1, ge=1, le=10, description="Number of bundles to purchase")


class CreateCheckoutSessionResponse(JsonModel):
    mode: Literal["payment"] = "payment"
    checkout_url: str
    session_id: str


class ConfirmSessionRequest(BaseModel):
    session_id: str


class ConfirmSessionResponse(JsonModel):
    """Response for session confirmation."""

    status: ConfirmSessionStatus = Field(..., description="Confirmation status")
    coins_added: int = Field(default=0, description="Number of coins added")


class StripePaymentStatus(StrEnum):
    PAID = "paid"
    UNPAID = "unpaid"
    NO_PAYMENT_REQUIRED = "no_payment_required"


class StripeSessionStatus(StrEnum):
    OPEN = "open"
    COMPLETE = "complete"
    EXPIRED = "expired"


class StripeMetadata(BaseModel):
    user_id: str | None = None
    coins: int | None = None
    bundle_id: str | None = None


class ConfirmableStripeSession(BaseModel):
    id: str
    payment_status: StripePaymentStatus | str = StripePaymentStatus.UNPAID
    status: StripeSessionStatus | str = StripeSessionStatus.OPEN
    metadata: StripeMetadata = Field(default_factory=StripeMetadata)


class CheckoutSessionResult(BaseModel):
    id: str
    url: str


class CheckoutSessionObject(BaseModel):
    id: str
    metadata: StripeMetadata = Field(default_factory=StripeMetadata)


class StripeEventData(BaseModel):
    object: CheckoutSessionObject


class CheckoutSessionCompletedEvent(BaseModel):
    id: str
    type: Literal["checkout.session.completed"]
    data: StripeEventData
