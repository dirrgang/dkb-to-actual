from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from dkb_to_actual.parsers.common import ParseError, Row, parse_amount, parse_date


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-10,99", "-10.99"),
        ("-34,6", "-34.60"),
        ("17,71", "17.71"),
        ("-1.000", "-1000"),
        ("3.456,78", "3456.78"),
        ("-10,99 €", "-10.99"),
        ("-42,00 EUR", "-42.00"),
        ("12,50-", "-12.50"),
        ("1\u00a0234,00", "1234.00"),
    ],
)
def test_parse_amount(text: str, expected: str) -> None:
    assert parse_amount(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "  ", "abc", "€"])
def test_parse_amount_rejects_garbage(text: str) -> None:
    with pytest.raises(ParseError):
        parse_amount(text)


@pytest.mark.parametrize("text", ["10.11.26", "10.11.2026", " 10.11.2026 "])
def test_parse_date(text: str) -> None:
    assert parse_date(text) == dt.date(2026, 11, 10)


def test_parse_date_rejects_invalid() -> None:
    with pytest.raises(ParseError, match="invalid date"):
        parse_date("2026-11-10")


def test_row_lookup_is_case_and_whitespace_insensitive() -> None:
    row = Row({"betrag (€)": 0, "status": 1}, [" -1,00 ", "Gebucht"])
    assert row.get("Betrag  (€)") == "-1,00"
    assert row.get("Missing", "Status") == "Gebucht"
    assert row.get("Missing") == ""
    with pytest.raises(ParseError, match="missing column"):
        row.require("Missing")
