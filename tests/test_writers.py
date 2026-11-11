from __future__ import annotations

import csv
import datetime as dt
import io
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import TYPE_CHECKING

from dkb_to_actual.convert import to_entries
from dkb_to_actual.models import AccountType, Statement, Transaction
from dkb_to_actual.reader import read_file
from dkb_to_actual.writers import write_csv, write_ofx

if TYPE_CHECKING:
    from pathlib import Path


def _ofx(statement: Statement) -> tuple[str, ET.Element]:
    out = io.StringIO()
    write_ofx(out, statement, to_entries(statement), today=dt.date(2026, 11, 11))
    text = out.getvalue()
    return text, ET.fromstring(text[text.index("<OFX>") :])  # noqa: S314 - self-generated


def test_csv(giro_csv: Path) -> None:
    st = read_file(giro_csv)
    out = io.StringIO()
    write_csv(out, st, to_entries(st))
    rows = list(csv.DictReader(io.StringIO(out.getvalue())))
    assert list(rows[0]) == ["Date", "Payee", "Notes", "Amount"]
    assert rows[0] == {
        "Date": "2026-11-02",
        "Payee": "Example Employer GmbH",
        "Notes": "Gehalt November 2026",
        "Amount": "3456.78",
    }
    assert sum(Decimal(r["Amount"]) for r in rows) == Decimal("2245.22")


def test_ofx_giro(giro_csv: Path) -> None:
    text, root = _ofx(read_file(giro_csv))
    assert text.startswith("OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\n")
    acct = root.find(".//BANKACCTFROM")
    assert acct is not None
    assert acct.findtext("BANKID") == "12030000"
    assert acct.findtext("ACCTID") == "DE00120300000000000001"
    txns = root.findall(".//STMTTRN")
    assert len(txns) == 8
    assert root.findtext(".//LEDGERBAL/BALAMT") == "1234.56"
    assert root.findtext(".//BANKTRANLIST/DTSTART") == "20261102"
    salary = txns[0]
    assert salary.findtext("TRNTYPE") == "CREDIT"
    assert salary.findtext("DTPOSTED") == "20261102"
    assert salary.findtext("TRNAMT") == "3456.78"
    assert salary.findtext("NAME") == "Example Employer GmbH"
    assert len({t.findtext("FITID") for t in txns}) == 8


def test_ofx_credit(credit_csv: Path) -> None:
    _, root = _ofx(read_file(credit_csv))
    assert root.find("CREDITCARDMSGSRSV1/CCSTMTTRNRS/CCSTMTRS") is not None
    assert root.findtext(".//CCACCTFROM/ACCTID") == "4930********0001"


def test_ofx_escapes_and_handles_missing_metadata() -> None:
    txn = Transaction(
        booking_date=dt.date(2026, 1, 1),
        value_date=None,
        amount=Decimal("-1"),
        payee="A & B <C>",
        notes="",
        raw=("x",),
    )
    text, root = _ofx(Statement(AccountType.GIRO, "", "", [txn]))
    assert "A &amp; B &lt;C&gt;" in text
    assert root.findtext(".//NAME") == "A & B <C>"
    assert root.find(".//MEMO") is None
    assert root.findtext(".//BANKID") == "DKB"
    assert root.find(".//LEDGERBAL") is None

    _, empty = _ofx(Statement(AccountType.CREDIT, "", ""))
    assert empty.findtext(".//DTSTART") == "20261111"
    assert empty.findtext(".//CCACCTFROM/ACCTID") == "DKB-KREDITKARTE"
