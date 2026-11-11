from __future__ import annotations

import datetime as dt
import os
from typing import TYPE_CHECKING

import pytest

from dkb_to_actual.files import latest_export, parse_since, permission_hint

if TYPE_CHECKING:
    from pathlib import Path


def test_latest_export_prefers_date_then_mtime(tmp_path: Path) -> None:
    older = tmp_path / "21-02-2026_Umsatzliste_Girokonto_DE00.csv"
    same_a = tmp_path / "21-06-2026_Umsatzliste_Girokonto_DE00.csv"
    same_b = tmp_path / "21-06-2026_Umsatzliste_Girokonto_DE00 (1).csv"
    ignored = tmp_path / "22-06-2026_Umsatzliste_Girokonto_DE00.actual.csv"
    invalid = tmp_path / "99-99-2026_Umsatzliste_Girokonto_DE00.csv"
    for p in (older, same_a, same_b, ignored, invalid):
        p.write_text("", encoding="utf-8")
    (tmp_path / "30-06-2026_Umsatzliste_Dir_x.csv").mkdir()
    os.utime(same_a, (1000, 1000))
    os.utime(same_b, (2000, 2000))
    assert latest_export(tmp_path) == same_b


def test_latest_export_none_found(tmp_path: Path) -> None:
    (tmp_path / "statement.csv").write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="no DKB export"):
        latest_export(tmp_path)


@pytest.mark.parametrize("text", ["2026-06-21", "21.06.2026", "21.06.26"])
def test_parse_since(text: str) -> None:
    assert parse_since(text) == dt.date(2026, 6, 21)


def test_parse_since_invalid() -> None:
    with pytest.raises(ValueError, match="invalid date"):
        parse_since("06/21/2026")


def test_permission_hint() -> None:
    assert permission_hint(PermissionError(13, "denied", "x.csv")).startswith(
        "x.csv: permission denied. Close the file"
    )
    assert permission_hint(PermissionError()).startswith("permission denied")
