from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dkb_to_actual.cli import app, default_output
from dkb_to_actual.writers import OutputFormat

runner = CliRunner(env={"COLUMNS": "200", "NO_COLOR": "1"})

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_BOX = re.compile(r"[│╭╮╰╯─┌┐└┘]")


def plain(output: str) -> str:
    """Rich forces colors and boxes on CI (GITHUB_ACTIONS); reduce to plain, unwrapped text."""
    return " ".join(_BOX.sub(" ", _ANSI.sub("", output)).split())


def test_default_output_next_to_input(tmp_path: Path, giro_csv: Path) -> None:
    source = tmp_path / giro_csv.name
    shutil.copy(giro_csv, source)
    result = runner.invoke(app, [str(source)])
    assert result.exit_code == 0, result.output
    out = tmp_path / "giro.actual.csv"
    assert out.read_text(encoding="utf-8").startswith("Date,Payee,Notes,Amount\n")
    assert "8 transactions, 1 skipped" in plain(result.output)


def test_default_output_name() -> None:
    assert default_output(Path("a/b.csv"), OutputFormat.OFX) == Path("a/b.actual.ofx")


def test_stdout_ofx(credit_csv: Path) -> None:
    result = runner.invoke(app, [str(credit_csv), "-f", "ofx", "-o", "-"])
    assert result.exit_code == 0, result.output
    assert "<CCSTMTRS>" in result.stdout


def test_options(giro_csv: Path) -> None:
    args = [
        str(giro_csv),
        "-o",
        "-",
        "--include-pending",
        "--since",
        "11.11.26",
        "--date",
        "value",
        "--no-payee-cleanup",
        "--type",
        "giro",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.stdout_bytes.splitlines()[1].startswith("2026-11-11,Example Café".encode())


def test_latest(tmp_path: Path, giro_csv: Path) -> None:
    shutil.copy(giro_csv, tmp_path / "11-11-2026_Umsatzliste_Girokonto_DE00.csv")
    result = runner.invoke(app, [str(tmp_path), "--latest"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "11-11-2026_Umsatzliste_Girokonto_DE00.actual.csv").exists()

    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 2
    assert "--latest" in plain(result.output)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--since", "nope"], "invalid date"),
        (["-o", "x.csv", "{giro}"], "single input"),
        (["-o", "{giro}"], "overwrite the input"),
    ],
)
def test_bad_parameters(giro_csv: Path, args: list[str], message: str) -> None:
    argv = [a.format(giro=giro_csv) for a in args] + [str(giro_csv)]
    result = runner.invoke(app, argv)
    assert result.exit_code == 2
    assert message in plain(result.output)


def test_parse_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("foo;bar\n", encoding="utf-8")
    result = runner.invoke(app, [str(bad)])
    assert result.exit_code == 1
    assert "unrecognized file" in plain(result.output)


def test_permission_error(tmp_path: Path, giro_csv: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(*_args: object, **_kwargs: object) -> int:
        raise PermissionError(13, "denied", "out.csv")

    monkeypatch.setattr(Path, "write_text", deny)
    result = runner.invoke(app, [str(giro_csv), "-o", str(tmp_path / "out.csv")])
    assert result.exit_code == 1
    assert "Close the file" in plain(result.output)


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("dkb-to-actual ")
