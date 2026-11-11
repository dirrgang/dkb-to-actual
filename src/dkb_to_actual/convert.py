"""Turn parsed statements into the records written for Actual."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from dkb_to_actual.payee import normalize_details

if TYPE_CHECKING:
    import datetime as dt
    from decimal import Decimal

    from dkb_to_actual.models import Statement, Transaction


class DateField(StrEnum):
    BOOKING = "booking"
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class Options:
    include_pending: bool = False
    date_field: DateField = DateField.BOOKING
    payee_cleanup: bool = True
    since: dt.date | None = None
    """Only keep entries dated on or after this day."""


@dataclass(frozen=True, slots=True)
class Entry:
    """A transaction as it will be imported into Actual."""

    date: dt.date
    payee: str
    notes: str
    amount: Decimal
    id: str
    """Stable id, used as OFX FITID (Actual's ``imported_id``)."""


def transaction_id(account_id: str, txn: Transaction, occurrence: int) -> str:
    """Derive a deterministic id from the original row.

    DKB exports carry no unique transaction id, so the id is a hash of the
    account and all original cells. ``occurrence`` disambiguates identical rows
    within one export (e.g. two equal coffee purchases on the same day).
    """
    material = "\x1f".join((account_id, *txn.raw, str(occurrence)))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def to_entries(statement: Statement, options: Options | None = None) -> list[Entry]:
    opts = options or Options()
    seen: Counter[tuple[str, ...]] = Counter()
    entries: list[Entry] = []
    for txn in statement.transactions:
        # Count before filtering so ids do not depend on --since / pending options.
        seen[txn.raw] += 1
        occurrence = seen[txn.raw]
        if txn.pending and not opts.include_pending:
            continue
        date = txn.booking_date
        if opts.date_field is DateField.VALUE and txn.value_date is not None:
            date = txn.value_date
        if opts.since is not None and date < opts.since:
            continue
        payee, notes = txn.payee, txn.notes
        if opts.payee_cleanup:
            payee, notes = normalize_details(payee, notes, txn.amount, txn.reference)
        entries.append(
            Entry(
                date=date,
                payee=payee,
                notes=notes,
                amount=txn.amount,
                id=transaction_id(statement.account_id, txn, occurrence),
            )
        )
    # Exports are newest-first; chronological order is nicer to review.
    entries.sort(key=lambda e: e.date)
    return entries
