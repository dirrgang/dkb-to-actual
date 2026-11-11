"""CSV output for Actual's import dialog."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TextIO

    from dkb_to_actual.convert import Entry
    from dkb_to_actual.models import Statement

HEADER = ("Date", "Payee", "Notes", "Amount")


def write_csv(out: TextIO, statement: Statement, entries: Iterable[Entry]) -> None:  # noqa: ARG001
    """Write ``Date,Payee,Notes,Amount`` with ISO dates and ``.`` as decimal separator.

    Actual maps these column names automatically on import.
    """
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HEADER)
    for e in entries:
        writer.writerow((e.date.isoformat(), e.payee, e.notes, f"{e.amount:.2f}"))
