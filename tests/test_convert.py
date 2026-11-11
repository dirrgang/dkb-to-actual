from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from dkb_to_actual.convert import DateField, Options, to_entries
from dkb_to_actual.reader import read_file

if TYPE_CHECKING:
    from pathlib import Path


def test_defaults(giro_csv: Path) -> None:
    entries = to_entries(read_file(giro_csv))
    assert len(entries) == 8  # pending skipped
    assert [e.date for e in entries] == sorted(e.date for e in entries)
    by_payee = {e.payee: e for e in entries}
    assert by_payee["Example Store GmbH"].notes == "PayPal purchase, reference 1000000000001"
    # PayPal without a merchant keeps the PayPal payee
    assert "PayPal Europe S.a.r.l. et Cie S.C.A" in by_payee


def test_ids_are_unique_and_stable(giro_csv: Path) -> None:
    first = to_entries(read_file(giro_csv))
    second = to_entries(read_file(giro_csv))
    assert [e.id for e in first] == [e.id for e in second]
    assert len({e.id for e in first}) == len(first)  # identical bakery rows differ
    assert all(len(e.id) == 32 for e in first)


def test_ids_do_not_depend_on_filters(giro_csv: Path) -> None:
    st = read_file(giro_csv)
    all_ids = {e.id for e in to_entries(st, Options(include_pending=True))}
    filtered = to_entries(st, Options(since=dt.date(2026, 11, 9)))
    assert len(filtered) == 4
    assert {e.id for e in filtered} <= all_ids


def test_include_pending_and_since(giro_csv: Path) -> None:
    st = read_file(giro_csv)
    entries = to_entries(st, Options(include_pending=True, since=dt.date(2026, 11, 10)))
    assert {e.date for e in entries} == {dt.date(2026, 11, 10), dt.date(2026, 11, 11)}
    assert len(entries) == 3


def test_value_date(giro_csv: Path) -> None:
    entries = to_entries(read_file(giro_csv), Options(date_field=DateField.VALUE))
    depot = next(e for e in entries if e.amount == Decimal("-1000"))
    assert depot.date == dt.date(2026, 11, 4)


def test_no_payee_cleanup(giro_csv: Path) -> None:
    entries = to_entries(read_file(giro_csv), Options(payee_cleanup=False))
    paypal = [e for e in entries if e.payee.startswith("PayPal")]
    assert len(paypal) == 2
    assert all("PP.5621.PP" in e.notes for e in paypal)
