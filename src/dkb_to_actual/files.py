"""Input/output path helpers."""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# e.g. "11-11-2026_Umsatzliste_Girokonto_DE00….csv" or "… (1).csv"; never our own output.
EXPORT_NAME = re.compile(
    r"^(?P<date>\d{2}-\d{2}-\d{4})_Umsatzliste_[^_]+_(?!.*\.actual\.csv$).+\.csv$",
    re.IGNORECASE,
)


def latest_export(directory: Path) -> Path:
    """Return the newest DKB export in ``directory`` (by export date, then mtime)."""
    candidates: list[tuple[dt.date, float, str, Path]] = []
    for child in directory.iterdir():
        match = EXPORT_NAME.match(child.name)
        if not match or not child.is_file():
            continue
        try:
            exported = dt.datetime.strptime(match["date"], "%d-%m-%Y").date()  # noqa: DTZ007
        except ValueError:
            continue
        candidates.append((exported, child.stat().st_mtime, child.name, child))
    if not candidates:
        raise FileNotFoundError(
            f"no DKB export (DD-MM-YYYY_Umsatzliste_*.csv) found in {directory}"
        )
    return max(candidates)[3]


def parse_since(text: str) -> dt.date:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return dt.datetime.strptime(text.strip(), fmt).date()  # noqa: DTZ007
        except ValueError:
            continue
    raise ValueError(f"invalid date {text!r}; use YYYY-MM-DD, DD.MM.YYYY or DD.MM.YY")


def permission_hint(err: PermissionError) -> str:
    """Explain the most common cause on Windows: the file is open in Excel."""
    where = f"{err.filename}: " if err.filename else ""
    return f"{where}permission denied. Close the file if it is open (e.g. in Excel) and try again."
