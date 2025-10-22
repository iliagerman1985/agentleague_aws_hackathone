"""Payment service to perform idempotent coin credits using a ledger."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import UserId
from common.utils.utils import get_logger
from shared_db.crud.payments import PaymentLedgerDAO
from shared_db.schemas.payments import StripePaymentLedgerEntry

from .user_service import UserService

logger = get_logger(__name__)


class PaymentService:
    def __init__(self, ledger_dao: PaymentLedgerDAO, user_service: UserService) -> None:
        self.ledger_dao = ledger_dao
        self.user_service = user_service

    async def credit_user_once(
        self,
        db: AsyncSession,
        *,
        stripe_session_id: str,
        user_id: UserId,
        coins: int,
    ) -> tuple[bool, int]:
        """Credit coins exactly once per Stripe session id.

        Returns (credited, coins_added)
        credited=False when a duplicate session-id is seen (no coins added).
        """
        ledger: StripePaymentLedgerEntry | None = await self.ledger_dao.insert_if_absent(
            db,
            stripe_session_id=stripe_session_id,
            user_id=user_id,
            coins=coins,
        )
        if ledger is None:
            return False, 0

        _ = await self.user_service.add_coins(db, user_id, coins)
        return True, coins
