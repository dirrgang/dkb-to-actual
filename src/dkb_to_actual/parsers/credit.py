"""Parser for DKB credit card (VISA) exports.

Column names differ between DKB banking generations, so lookups accept
several aliases:

* new: ``Belegdatum;Wertstellung;Status;Beschreibung;Umsatztyp;Betrag (€);Fremdwährungsbetrag``
* old: ``Umsatz abgerechnet und nicht im Saldo enthalten;Wertstellung;Belegdatum;
  Beschreibung;Betrag (EUR);Ursprünglicher Betrag``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dkb_to_actual.models import Transaction
from dkb_to_actual.parsers.common import ParseError, parse_amount, parse_date, parse_optional_date
from dkb_to_actual.payee import clean_party, collapse_whitespace

if TYPE_CHECKING:
    from dkb_to_actual.parsers.common import Row

HEADER_MARKERS = frozenset({"beschreibung", "wertstellung"})

_DATE_COLUMNS = ("Belegdatum", "Buchungsdatum", "Wertstellung")
_AMOUNT_COLUMNS = ("Betrag (€)", "Betrag (EUR)", "Betrag")
_FOREIGN_COLUMNS = ("Fremdwährungsbetrag", "Ursprünglicher Betrag")
_SETTLED_COLUMN = "Umsatz abgerechnet und nicht im Saldo enthalten"


def _is_pending(row: Row) -> bool:
    if row.get("Status").lower() == "vorgemerkt":
        return True
    # Old layout: "Nein" = not yet settled.
    return row.get(_SETTLED_COLUMN).lower() == "nein"


def parse_row(row: Row) -> Transaction:
    date_text = row.get(*_DATE_COLUMNS)
    if not date_text:
        raise ParseError(f"missing date (expected one of {', '.join(_DATE_COLUMNS)})")
    foreign = collapse_whitespace(row.get(*_FOREIGN_COLUMNS))
    amount_text = row.require(*_AMOUNT_COLUMNS)
    return Transaction(
        booking_date=parse_date(date_text),
        value_date=parse_optional_date(row.get("Wertstellung")),
        amount=parse_amount(amount_text),
        payee=clean_party(row.require("Beschreibung")),
        notes=f"Fremdwährung: {foreign}" if foreign and foreign != amount_text else "",
        pending=_is_pending(row),
        reference=row.get("Kundenreferenz"),
        raw=row.cells,
    )
