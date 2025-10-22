"""StripeService encapsulates all Stripe interactions.
Reads configuration from ConfigService and exposes methods for bundles and checkout sessions.
"""

from __future__ import annotations

import json
from pathlib import Path

import stripe

from app.schemas.billing import CheckoutSessionResult, CoinBundle
from common.core.config_service import ConfigService
from common.utils.utils import get_logger
from shared_db.schemas.user import UserResponse

logger = get_logger()


class StripeConfigError(Exception):
    pass


class StripeAPIError(Exception):
    pass


class StripeCheckoutError(Exception):
    pass


class StripeService:
    def __init__(self, config: ConfigService) -> None:
        self.config = config
        api_key = self.config.stripe.api_key
        self.webhook_secret = str(self.config.stripe.webhook_secret or "")
        self.success_url = str(self.config.stripe.success_url or "")
        self.cancel_url = str(self.config.stripe.cancel_url or "")

        # Strict config validation
        if not api_key:
            logger.exception("Stripe API key is missing in configuration")
            raise StripeConfigError("Stripe API key is not set in config")
        if not self.webhook_secret:
            logger.exception("Stripe webhook secret is missing in configuration")
            raise StripeConfigError("Stripe webhook_secret is not set in config")

        stripe.api_key = str(api_key)

        # Load bundles config
        self._bundles = self._load_bundles()

    def _bundles_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "config" / "coin_bundles.json"

    def _load_bundles(self) -> list[CoinBundle]:
        path = self._bundles_path()
        if not path.exists():
            logger.warning("coin_bundles.json not found at %s; using empty bundle list", path)
            return []
        try:
            data = json.loads(path.read_text())
            bundles = [CoinBundle(**b) for b in data.get("bundles", [])]
            return bundles
        except Exception as e:
            logger.exception("Failed to load coin bundles: %s", e)
            return []

    def get_bundles(self) -> list[CoinBundle]:
        # Reload on each call in case file updated
        self._bundles = self._load_bundles()
        return self._bundles

    async def create_checkout_session(self, user: UserResponse, bundle_id: str, quantity: int = 1) -> CheckoutSessionResult:
        bundles = {b.id: b for b in self.get_bundles()}
        bundle = bundles.get(bundle_id)
        if not bundle:
            raise StripeCheckoutError("Invalid bundle_id")
        if not bundle.price_id:
            raise StripeCheckoutError("Bundle missing Stripe price_id; admin must generate prices and update coin_bundles.json")
        if not self.success_url or not self.cancel_url:
            raise StripeCheckoutError("Stripe success_url/cancel_url are not configured")
        if quantity < 1:
            raise StripeCheckoutError("Quantity must be >= 1")

        logger.info(
            "Creating Stripe Checkout Session",
            extra={"user_id": str(user.id), "bundle_id": bundle_id, "quantity": quantity},
        )

        try:
            # Ensure success_url includes the checkout session id for client-side confirmation flow
            success_with_session = f"{self.success_url}{'&' if '?' in self.success_url else '?'}session_id={{CHECKOUT_SESSION_ID}}"
            session = stripe.checkout.Session.create(
                mode="payment",
                success_url=success_with_session,
                cancel_url=self.cancel_url,
                client_reference_id=str(user.id),
                metadata={
                    "user_id": str(user.id),
                    "bundle_id": bundle.id,
                    "coins": str(bundle.coins * quantity),
                },
                line_items=[{"price": bundle.price_id, "quantity": quantity}],
            )
        except stripe.error.AuthenticationError as e:
            logger.exception("Stripe authentication error")
            raise StripeCheckoutError("Stripe authentication failed") from e
        except stripe.error.InvalidRequestError as e:
            logger.exception("Stripe invalid request")
            raise StripeCheckoutError("Invalid Stripe request") from e
        except stripe.error.RateLimitError as e:
            logger.exception("Stripe rate limit exceeded")
            raise StripeCheckoutError("Stripe rate limit exceeded") from e
        except stripe.error.APIConnectionError as e:
            logger.exception("Stripe API connection error")
            raise StripeCheckoutError("Stripe API connection error") from e
        except stripe.error.APIError as e:
            logger.exception("Stripe API error")
            raise StripeCheckoutError("Stripe API error") from e
        except stripe.error.StripeError as e:
            # Fallback for any other Stripe-specific errors
            logger.exception("Generic Stripe error")
            raise StripeCheckoutError("Stripe error") from e
        except Exception as e:
            logger.exception("Unexpected error creating Stripe Checkout Session")
            raise StripeAPIError("Unexpected error while creating checkout session") from e

        return CheckoutSessionResult(id=session.id, url=session.url)
