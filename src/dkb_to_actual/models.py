"""Core data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt
    from decimal import Decimal


class AccountType(StrEnum):
    """Kind of DKB account an export belongs to."""

    GIRO = "giro"
    """Girokonto or Tagesgeld (both share the same export layout)."""
    CREDIT = "credit"
    """Kreditkarte."""


@dataclass(frozen=True, slots=True)
class Transaction:
    """A single, normalized transaction."""

    booking_date: dt.date
    value_date: dt.date | None
    amount: Decimal
    """Signed amount in EUR; negative means money leaving the account."""
    payee: str
    notes: str
    pending: bool = False
    counterparty_iban: str = ""
    reference: str = ""
    """Bank-provided reference (e.g. Kundenreferenz), may be empty."""
    raw: tuple[str, ...] = ()
    """Original CSV cells, used to derive a stable transaction id."""


@dataclass(frozen=True, slots=True)
class Statement:
    """All transactions parsed from one export file."""

    account_type: AccountType
    account_id: str
    """IBAN for Giro/Tagesgeld, masked card number for credit cards."""
    account_name: str
    transactions: list[Transaction] = field(default_factory=list[Transaction])
    balance: Decimal | None = None
    balance_date: dt.date | None = None
