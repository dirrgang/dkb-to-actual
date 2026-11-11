"""Command line interface."""

from __future__ import annotations

import io
from enum import StrEnum
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from dkb_to_actual.convert import DateField, Options, to_entries
from dkb_to_actual.files import latest_export, parse_since, permission_hint
from dkb_to_actual.models import AccountType
from dkb_to_actual.parsers.common import ParseError
from dkb_to_actual.reader import read_file
from dkb_to_actual.writers import WRITERS, OutputFormat

app = typer.Typer(
    help="Convert DKB CSV exports into CSV or OFX files that Actual Budget can import.",
    add_completion=False,
    no_args_is_help=True,
)

STDOUT = Path("-")


class TypeChoice(StrEnum):
    AUTO = "auto"
    GIRO = "giro"
    CREDIT = "credit"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"dkb-to-actual {version('dkb-to-actual')}")
        raise typer.Exit


def default_output(source: Path, fmt: OutputFormat) -> Path:
    return source.with_name(f"{source.stem}.actual.{fmt.value}")


@app.command()
def main(
    inputs: Annotated[
        list[Path],
        typer.Argument(
            help="DKB CSV export(s), or a directory together with --latest.",
            exists=True,
            readable=True,
            show_default=False,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file, or '-' for stdout. Defaults to <input>.actual.<format>. "
            "Only allowed with a single input.",
            show_default=False,
        ),
    ] = None,
    fmt: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format.")
    ] = OutputFormat.CSV,
    account_type: Annotated[
        TypeChoice, typer.Option("--type", "-t", help="Export type; auto-detected by default.")
    ] = TypeChoice.AUTO,
    include_pending: Annotated[
        bool,
        typer.Option("--include-pending", help="Include pending ('Vorgemerkt') transactions."),
    ] = False,
    date_field: Annotated[
        DateField,
        typer.Option("--date", help="Use booking date or value date (Wertstellung)."),
    ] = DateField.BOOKING,
    payee_cleanup: Annotated[
        bool,
        typer.Option(
            "--payee-cleanup/--no-payee-cleanup",
            help="Use the merchant instead of 'PayPal' as payee where possible.",
        ),
    ] = True,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            help="Only keep transactions on or after this date "
            "(YYYY-MM-DD, DD.MM.YYYY or DD.MM.YY).",
            show_default=False,
        ),
    ] = None,
    latest: Annotated[
        bool,
        typer.Option(
            "--latest",
            help="For a directory input, convert the newest DKB export in it.",
        ),
    ] = False,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    """Convert DKB CSV exports (Girokonto, Tagesgeld, Kreditkarte) for Actual Budget."""
    if output is not None and len(inputs) > 1:
        raise typer.BadParameter("--output can only be used with a single input file")
    try:
        since_date = parse_since(since) if since else None
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--since") from exc

    forced = None if account_type is TypeChoice.AUTO else AccountType(account_type.value)
    options = Options(
        include_pending=include_pending,
        date_field=date_field,
        payee_cleanup=payee_cleanup,
        since=since_date,
    )
    try:
        for source in inputs:
            _convert_one(_resolve_input(source, latest=latest), output, fmt, forced, options)
    except PermissionError as exc:
        _fail(permission_hint(exc))
    except (ParseError, FileNotFoundError) as exc:
        _fail(str(exc))


def _fail(message: str) -> NoReturn:
    typer.secho(f"error: {message}", err=True, fg=typer.colors.RED)
    raise typer.Exit(code=1)


def _resolve_input(source: Path, *, latest: bool) -> Path:
    if not source.is_dir():
        return source
    if not latest:
        raise typer.BadParameter(
            f"{source} is a directory; use --latest to pick the newest DKB export in it"
        )
    chosen = latest_export(source)
    typer.echo(f"Selected input: {chosen}", err=True)
    return chosen


def _convert_one(
    source: Path,
    output: Path | None,
    fmt: OutputFormat,
    forced: AccountType | None,
    options: Options,
) -> None:
    target = output or default_output(source, fmt)
    if target != STDOUT and target.resolve() == source.resolve():
        raise typer.BadParameter(f"output would overwrite the input file: {source}")
    try:
        statement = read_file(source, forced)
    except ParseError as exc:
        raise ParseError(f"{source}: {exc}") from exc

    entries = to_entries(statement, options)
    buffer = io.StringIO()
    WRITERS[fmt](buffer, statement, entries)

    summary = f"{source.name}: {len(entries)} transactions"
    if skipped := len(statement.transactions) - len(entries):
        summary += f", {skipped} skipped (pending or before --since)"
    if target == STDOUT:
        # Always UTF-8, regardless of the console code page (cp1252/cp850 on Windows).
        stdout = typer.get_binary_stream("stdout")
        stdout.write(buffer.getvalue().encode("utf-8"))
        stdout.flush()
        typer.echo(summary, err=True)
    else:
        target.write_text(buffer.getvalue(), encoding="utf-8", newline="")
        typer.echo(f"{summary} -> {target}", err=True)
