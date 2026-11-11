"""Parser for DKB Girokonto / Tagesgeld exports (new banking, 2023+)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dkb_to_actual.models import Transaction
from dkb_to_actual.parsers.common import parse_amount, parse_date, parse_optional_date
from dkb_to_actual.payee import clean_party, collapse_whitespace

if TYPE_CHECKING:
    from dkb_to_actual.parsers.common import Row

HEADER_MARKERS = frozenset({"buchungsdatum", "zahlungsempfänger*in", "verwendungszweck"})

PENDING_STATUS = "vorgemerkt"


def parse_row(row: Row) -> Transaction:
    amount = parse_amount(row.require("Betrag (€)", "Betrag (EUR)", "Betrag"))
    payer = row.get("Zahlungspflichtige*r")
    recipient = row.get("Zahlungsempfänger*in")
    purpose = collapse_whitespace(row.get("Verwendungszweck"))
    counterparty = recipient if amount < 0 else payer
    return Transaction(
        booking_date=parse_date(row.require("Buchungsdatum")),
        value_date=parse_optional_date(row.get("Wertstellung")),
        amount=amount,
        payee=clean_party(counterparty),
        notes=purpose,
        pending=row.get("Status").lower() == PENDING_STATUS,
        counterparty_iban=row.get("IBAN"),
        reference=row.get("Kundenreferenz"),
        raw=row.cells,
    )
