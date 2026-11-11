"""Read DKB CSV exports and detect their format."""

from __future__ import annotations

import csv
import io
import re
from typing import TYPE_CHECKING

from dkb_to_actual.models import AccountType, Statement
from dkb_to_actual.parsers import credit, giro
from dkb_to_actual.parsers.common import ParseError, Row, normalize_header, parse_amount, parse_date

if TYPE_CHECKING:
    from pathlib import Path

_MARKERS: dict[AccountType, frozenset[str]] = {
    AccountType.GIRO: giro.HEADER_MARKERS,
    AccountType.CREDIT: credit.HEADER_MARKERS,
}
_ROW_PARSERS = {
    AccountType.GIRO: giro.parse_row,
    AccountType.CREDIT: credit.parse_row,
}
_BALANCE_LABEL = re.compile(r"^(kontostand|saldo) vom (?P<date>[\d.]+):?$", re.IGNORECASE)
# Only scan this many leading rows for the header to fail fast on unrelated files.
_MAX_PREAMBLE_ROWS = 20


def decode(data: bytes) -> str:
    """Decode export bytes: UTF-8 (with or without BOM), falling back to Windows-1252."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def detect_type(header: list[str]) -> AccountType | None:
    names = {normalize_header(h) for h in header}
    for account_type, markers in _MARKERS.items():
        if markers <= names:
            return account_type
    return None


def read_file(path: Path, account_type: AccountType | None = None) -> Statement:
    return parse_text(decode(path.read_bytes()), account_type)


def parse_text(text: str, account_type: AccountType | None = None) -> Statement:
    """Parse the textual content of a DKB export."""
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))

    header_pos: int | None = None
    detected: AccountType | None = None
    for pos, cells in enumerate(rows[:_MAX_PREAMBLE_ROWS]):
        detected = detect_type(cells)
        if detected is not None:
            header_pos = pos
            break

    if header_pos is None or detected is None:
        first = next((r for r in rows if any(c.strip() for c in r)), [])
        raise ParseError(
            "unrecognized file: no DKB Girokonto/Tagesgeld or Kreditkarte header found "
            f"(first row: {first!r})"
        )
    if account_type is not None and account_type is not detected:
        raise ParseError(f"expected a {account_type} export but detected {detected}")

    statement = _parse_preamble(rows[:header_pos], detected)
    index = {normalize_header(h): i for i, h in enumerate(rows[header_pos])}
    parse_row = _ROW_PARSERS[detected]
    for line_no, cells in enumerate(rows[header_pos + 1 :], start=header_pos + 2):
        if not any(c.strip() for c in cells):
            continue
        try:
            statement.transactions.append(parse_row(Row(index, cells)))
        except ParseError as exc:
            raise ParseError(f"line {line_no}: {exc}") from exc
    return statement


def _parse_preamble(rows: list[list[str]], account_type: AccountType) -> Statement:
    """Extract account metadata from the rows above the header."""
    account_name = ""
    account_id = ""
    balance = None
    balance_date = None
    for cells in rows:
        values = [c.strip() for c in cells if c.strip()]
        if not values:
            continue
        match = _BALANCE_LABEL.match(values[0])
        if match and len(values) >= 2:
            try:
                balance = parse_amount(values[1])
                balance_date = parse_date(match.group("date"))
            except ParseError:
                balance = balance_date = None
        elif not account_name and len(values) >= 2:
            # Giro:   "Girokonto";"DE12…"
            # Credit: "Karte";"Visa Kreditkarte";"4930 **** **** 1234"
            # Old credit: "Kreditkarte:";"4748********1234 Kreditkarte"
            account_name = (values[-2] if len(values) > 2 else values[0]).rstrip(":")
            account_id = values[-1]
            parts = account_id.split()
            if len(parts) > 1 and parts[-1].isalpha():
                account_id = " ".join(parts[:-1])
    return Statement(
        account_type=account_type,
        account_id=account_id.replace(" ", ""),
        account_name=account_name,
        balance=balance,
        balance_date=balance_date,
    )
