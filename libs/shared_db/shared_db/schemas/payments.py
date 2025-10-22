"""Pydantic schemas for payment ledger."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from common.ids import UserId
from common.utils.tsid import TSID


class LedgerStatus(StrEnum):
    CREDITED = "credited"


class StripePaymentLedgerEntry(BaseModel):
    id: TSID
    stripe_session_id: str
    user_id: UserId
    coins: int
    status: LedgerStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
