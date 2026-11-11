"""OFX output.

Written as OFX 1.0.2 with explicit closing tags on every element. That keeps it
valid SGML for strict OFX readers while also being well-formed XML, which is
what Actual's importer tries first. Actual uses ``FITID`` as ``imported_id``,
so re-importing overlapping exports does not create duplicates.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from dkb_to_actual.models import AccountType

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import TextIO

    from dkb_to_actual.convert import Entry
    from dkb_to_actual.models import Statement

_HEADER = """\
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UNICODE
CHARSET:NONE
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

"""


def _date(value: dt.date) -> str:
    return value.strftime("%Y%m%d")


def _el(tag: str, value: str) -> str:
    return f"<{tag}>{escape(' '.join(value.split()))}</{tag}>"


def _bank_id(iban: str) -> str:
    # German IBAN: DEkk BBBBBBBB CCCCCCCCCC -> BLZ is characters 5-12.
    if iban.upper().startswith("DE") and len(iban) == 22:
        return iban[4:12]
    return "DKB"


def _transactions(entries: list[Entry]) -> Iterator[str]:
    for e in entries:
        yield "<STMTTRN>"
        yield _el("TRNTYPE", "CREDIT" if e.amount > 0 else "DEBIT")
        yield _el("DTPOSTED", _date(e.date))
        yield _el("TRNAMT", f"{e.amount:.2f}")
        yield _el("FITID", e.id)
        if e.payee:
            yield _el("NAME", e.payee)
        if e.notes:
            yield _el("MEMO", e.notes)
        yield "</STMTTRN>"


def _statement_body(statement: Statement, entries: list[Entry], today: dt.date) -> Iterator[str]:
    start = min((e.date for e in entries), default=today)
    end = max((e.date for e in entries), default=today)
    yield _el("CURDEF", "EUR")
    if statement.account_type is AccountType.CREDIT:
        yield "<CCACCTFROM>"
        yield _el("ACCTID", statement.account_id or "DKB-KREDITKARTE")
        yield "</CCACCTFROM>"
    else:
        yield "<BANKACCTFROM>"
        yield _el("BANKID", _bank_id(statement.account_id))
        yield _el("ACCTID", statement.account_id or "DKB-GIROKONTO")
        yield _el("ACCTTYPE", "CHECKING")
        yield "</BANKACCTFROM>"
    yield "<BANKTRANLIST>"
    yield _el("DTSTART", _date(start))
    yield _el("DTEND", _date(end))
    yield from _transactions(entries)
    yield "</BANKTRANLIST>"
    if statement.balance is not None:
        yield "<LEDGERBAL>"
        yield _el("BALAMT", f"{statement.balance:.2f}")
        yield _el("DTASOF", _date(statement.balance_date or end))
        yield "</LEDGERBAL>"


def write_ofx(
    out: TextIO,
    statement: Statement,
    entries: Iterable[Entry],
    *,
    today: dt.date | None = None,
) -> None:
    today = today or dt.datetime.now(tz=dt.UTC).date()
    items = list(entries)
    if statement.account_type is AccountType.CREDIT:
        msgs, trnrs, stmtrs = "CREDITCARDMSGSRSV1", "CCSTMTTRNRS", "CCSTMTRS"
    else:
        msgs, trnrs, stmtrs = "BANKMSGSRSV1", "STMTTRNRS", "STMTRS"

    status = ["<STATUS>", _el("CODE", "0"), _el("SEVERITY", "INFO"), "</STATUS>"]
    lines = [
        "<OFX>",
        "<SIGNONMSGSRSV1>",
        "<SONRS>",
        *status,
        _el("DTSERVER", _date(today)),
        _el("LANGUAGE", "DEU"),
        "</SONRS>",
        "</SIGNONMSGSRSV1>",
        f"<{msgs}>",
        f"<{trnrs}>",
        _el("TRNUID", "0"),
        *status,
        f"<{stmtrs}>",
        *_statement_body(statement, items, today),
        f"</{stmtrs}>",
        f"</{trnrs}>",
        f"</{msgs}>",
        "</OFX>",
    ]
    out.write(_HEADER)
    out.write("\n".join(lines))
    out.write("\n")
