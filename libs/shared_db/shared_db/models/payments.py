"""Payment-related database models.
Idempotency ledger to ensure we never double-credit coins for the same Stripe session.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from common.db.db_utils import DbTSID
from common.ids import UserId
from common.utils.tsid import TSID
from shared_db.db import Base


class LedgerStatus(StrEnum):
    CREDITED = "credited"


class StripePaymentLedger(Base):
    """Idempotency ledger keyed by Stripe checkout session id."""

    __tablename__ = "stripe_payment_ledger"
    __table_args__ = (UniqueConstraint("stripe_session_id", name="uq_stripe_payment_ledger_session"),)

    id: Mapped[TSID] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)

    stripe_session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[UserId] = mapped_column(DbTSID(), nullable=False, index=True)
    coins: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[LedgerStatus] = mapped_column(String(32), nullable=False, default=LedgerStatus.CREDITED)
