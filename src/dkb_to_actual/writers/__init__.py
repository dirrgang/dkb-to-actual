"""Output writers."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from dkb_to_actual.writers.csv import write_csv
from dkb_to_actual.writers.ofx import write_ofx

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import TextIO

    from dkb_to_actual.convert import Entry
    from dkb_to_actual.models import Statement


class OutputFormat(StrEnum):
    CSV = "csv"
    OFX = "ofx"


WRITERS: dict[OutputFormat, Callable[[TextIO, Statement, Iterable[Entry]], None]] = {
    OutputFormat.CSV: write_csv,
    OutputFormat.OFX: write_ofx,
}

__all__ = ["WRITERS", "OutputFormat", "write_csv", "write_ofx"]
