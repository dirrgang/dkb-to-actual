from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from dkb_to_actual.models import AccountType
from dkb_to_actual.parsers.common import ParseError
from dkb_to_actual.reader import decode, parse_text, read_file

if TYPE_CHECKING:
    from pathlib import Path


def test_decode_handles_bom_and_cp1252() -> None:
    assert decode("﻿ä".encode()) == "ä"
    assert decode("ä".encode("cp1252")) == "ä"


def test_giro(giro_csv: Path) -> None:
    st = read_file(giro_csv)
    assert st.account_type is AccountType.GIRO
    assert st.account_id == "DE00120300000000000001"
    assert st.account_name == "Girokonto"
    assert st.balance == Decimal("1234.56")
    assert st.balance_date == dt.date(2026, 11, 11)
    assert len(st.transactions) == 9

    pending = st.transactions[0]
    assert pending.pending
    assert pending.payee == "Example Café"

    salary = st.transactions[-1]
    assert salary.amount == Decimal("3456.78")
    assert salary.payee == "Example Employer GmbH"  # incoming -> payer

    marketplace = st.transactions[5]
    assert marketplace.payee == "Example Marketplace S.a.r.l."  # padded address stripped

    depot = st.transactions[7]
    assert depot.amount == Decimal("-1000")
    assert depot.booking_date == dt.date(2026, 11, 3)
    assert depot.value_date == dt.date(2026, 11, 4)
    assert "Preis 50,90000000 EUR" in depot.notes


def test_credit(credit_csv: Path) -> None:
    st = read_file(credit_csv)
    assert st.account_type is AccountType.CREDIT
    assert st.account_id == "4930********0001"
    assert st.account_name == "Visa Kreditkarte"
    assert st.balance == Decimal("-123.45")
    pending, cloud, settlement = st.transactions
    assert pending.pending
    assert cloud.payee == "EXAMPLE CLOUD INC"
    assert cloud.amount == Decimal("-18.37")
    assert cloud.notes == "Fremdwährung: -20,00 USD"
    assert cloud.booking_date == dt.date(2026, 11, 8)
    assert settlement.amount == Decimal("500.00")


def test_credit_legacy(credit_legacy_csv: Path) -> None:
    st = read_file(credit_legacy_csv)
    assert st.account_type is AccountType.CREDIT
    assert st.account_id == "4748********0001"
    assert st.account_name == "Kreditkarte"
    bakery, streaming = st.transactions
    assert bakery.payee == "BÄCKEREI BEISPIEL"
    assert bakery.pending  # "Nein" = not yet settled
    assert not streaming.pending
    assert streaming.booking_date == dt.date(2026, 10, 1)
    assert streaming.notes == "Fremdwährung: -11,49 USD"


def test_forced_type_mismatch(giro_csv: Path) -> None:
    with pytest.raises(ParseError, match="expected a credit export"):
        read_file(giro_csv, AccountType.CREDIT)


def test_unrecognized_file() -> None:
    with pytest.raises(ParseError, match="unrecognized file"):
        parse_text("Date,Payee,Amount\n2026-01-01,X,1\n")


def test_bad_row_reports_line_number() -> None:
    text = (
        '"Buchungsdatum";"Wertstellung";"Status";"Zahlungspflichtige*r";"Zahlungsempfänger*in";'
        '"Verwendungszweck";"Betrag (€)"\n'
        '"01.01.26";"01.01.26";"Gebucht";"A";"B";"C";"oops"\n'
    )
    with pytest.raises(ParseError, match=r"line 2: invalid amount"):
        parse_text(text)


def test_credit_row_without_date() -> None:
    text = '"Wertstellung";"Beschreibung";"Betrag (€)"\n"";"X";"-1,00"\n'
    with pytest.raises(ParseError, match="missing date"):
        parse_text(text)


def test_invalid_balance_is_ignored() -> None:
    text = (
        '"Girokonto";"DE00"\n"Kontostand vom 11.11.2026:";"n/a"\n'
        '"Buchungsdatum";"Zahlungsempfänger*in";"Verwendungszweck";"Betrag (€)"\n'
    )
    st = parse_text(text)
    assert st.balance is None
    assert st.transactions == []
