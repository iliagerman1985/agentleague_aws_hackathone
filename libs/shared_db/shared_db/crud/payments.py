"""DAO for payment ledger operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import UserId
from common.utils.utils import get_logger
from shared_db.models.payments import LedgerStatus, StripePaymentLedger
from shared_db.schemas.payments import StripePaymentLedgerEntry

logger = get_logger(__name__)


class PaymentLedgerDAO:
    async def insert_if_absent(
        self,
        db: AsyncSession,
        *,
        stripe_session_id: str,
        user_id: UserId,
        coins: int,
    ) -> StripePaymentLedgerEntry | None:
        """Insert a ledger entry if session_id not seen before.
        Returns the created entry, or None if duplicate.
        """
        entry = StripePaymentLedger(
            stripe_session_id=stripe_session_id,
            user_id=user_id,
            coins=coins,
            status=LedgerStatus.CREDITED,
        )
        try:
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            return StripePaymentLedgerEntry.model_validate(entry)
        except IntegrityError:
            logger.info("Duplicate stripe_session_id, skipping credit", extra={"stripe_session_id": stripe_session_id})
            await db.rollback()
            return None

    async def get_by_session_id(self, db: AsyncSession, *, stripe_session_id: str) -> StripePaymentLedgerEntry | None:
        result = await db.execute(select(StripePaymentLedger).where(StripePaymentLedger.stripe_session_id == stripe_session_id))
        row = result.scalar_one_or_none()
        return StripePaymentLedgerEntry.model_validate(row) if row else None
