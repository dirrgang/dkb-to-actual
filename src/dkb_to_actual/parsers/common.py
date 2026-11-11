"""Parsing helpers shared by all DKB formats."""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation


class ParseError(ValueError):
    """Raised when an export cannot be parsed."""


_AMOUNT_JUNK = re.compile(r"[\s€]|EUR", re.IGNORECASE)


def parse_amount(text: str) -> Decimal:
    """Parse a German-formatted amount such as ``-1.234,56 €`` into a Decimal."""
    cleaned = _AMOUNT_JUNK.sub("", text)
    if not cleaned:
        raise ParseError(f"empty amount: {text!r}")
    cleaned = cleaned.replace(".", "").replace(",", ".")
    # Some exports use a trailing minus sign ("12,50-").
    if cleaned.endswith("-"):
        cleaned = "-" + cleaned[:-1]
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ParseError(f"invalid amount: {text!r}") from exc


def parse_date(text: str) -> dt.date:
    """Parse ``dd.mm.yy`` or ``dd.mm.yyyy`` into a date."""
    value = text.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return dt.datetime.strptime(value, fmt).date()  # noqa: DTZ007 - date only
        except ValueError:
            continue
    raise ParseError(f"invalid date: {text!r}")


def parse_optional_date(text: str) -> dt.date | None:
    """Like :func:`parse_date`, but returns None for empty cells."""
    return parse_date(text) if text.strip() else None


def normalize_header(text: str) -> str:
    """Normalize a header cell for robust column lookup."""
    return re.sub(r"\s+", " ", text.strip().lower())


class Row:
    """Dict-like access to a CSV row by (normalized) header name."""

    __slots__ = ("_cells", "_index")

    def __init__(self, index: dict[str, int], cells: list[str]) -> None:
        self._index = index
        self._cells = cells

    def get(self, *names: str) -> str:
        """Return the first present column among ``names`` (stripped), or ``""``."""
        for name in names:
            pos = self._index.get(normalize_header(name))
            if pos is not None and pos < len(self._cells):
                return self._cells[pos].strip()
        return ""

    def require(self, *names: str) -> str:
        """Like :meth:`get`, but the column must exist in the header."""
        if not any(normalize_header(n) in self._index for n in names):
            raise ParseError(f"missing column: {' / '.join(names)}")
        return self.get(*names)

    @property
    def cells(self) -> tuple[str, ...]:
        return tuple(self._cells)
