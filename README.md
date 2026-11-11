# dkb-to-actual

[![CI](https://github.com/dirrgang/dkb-to-actual/actions/workflows/ci.yml/badge.svg)](https://github.com/dirrgang/dkb-to-actual/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dkb-to-actual)](https://pypi.org/project/dkb-to-actual/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Convert CSV exports from [DKB](https://www.dkb.de/) (Girokonto, Tagesgeld, Kreditkarte) into
files that [Actual Budget](https://actualbudget.org/) can import, either as **CSV** or as **OFX**.

DKB exports are not directly importable: they start with metadata rows, use `;` as separator,
German number and date formats (`-1.234,56`, `10.11.26`) and put the payee into different
columns depending on the direction of the payment. `dkb-to-actual` takes care of that and also
cleans up a few DKB quirks:

- **PayPal**: the real merchant (`… Ihr Einkauf bei <merchant>`) becomes the payee, the noisy
  purpose text becomes a short note such as `PayPal purchase, reference 1054298385875`.
- Party fields padded with an address (`Example S.a.r.l.      Example Street 1`) are trimmed.
- Pending transactions (`Vorgemerkt`) are skipped by default, as they change once booked.
- Every transaction gets a stable id derived from the original row. In OFX files it is used as
  `FITID`, which Actual stores as `imported_id`, so importing **overlapping exports does not
  create duplicates**.

Everything runs locally and offline. No data leaves your machine.

## Installation

```sh
uv tool install dkb-to-actual     # or: pipx install dkb-to-actual
# one-off without installing:
uvx dkb-to-actual export.csv
```

## Usage

Download the transactions in DKB banking (*Umsätze → Export → CSV*), then:

```sh
# CSV next to the input: 11-11-2026_Umsatzliste_Girokonto_….actual.csv
dkb-to-actual 11-11-2026_Umsatzliste_Girokonto_DE00….csv

# OFX (recommended for repeated imports, thanks to duplicate detection)
dkb-to-actual -f ofx 11-11-2026_Umsatzliste_Girokonto_DE00….csv

# newest DKB export in a directory, only from a given date on
dkb-to-actual --latest ~/Downloads --since 2026-11-01

# preview on stdout
dkb-to-actual export.csv -o -
```

| Option | Description |
| --- | --- |
| `-f, --format csv\|ofx` | Output format (default `csv`). |
| `-o, --output PATH` | Output file, `-` for stdout. Default: `<input>.actual.<format>`. |
| `-t, --type auto\|giro\|credit` | Export type, auto-detected from the header by default. |
| `--date booking\|value` | Use Buchungsdatum/Belegdatum (default) or Wertstellung. |
| `--since DATE` | Only transactions on/after `YYYY-MM-DD`, `DD.MM.YYYY` or `DD.MM.YY`. |
| `--latest` | With a directory input: use the newest `DD-MM-YYYY_Umsatzliste_*.csv`. |
| `--include-pending` | Also export pending (`Vorgemerkt`) transactions. |
| `--no-payee-cleanup` | Keep payee and notes exactly as DKB provides them. |

### Importing into Actual

1. Open the account in Actual and click **Import**.
2. Pick the generated file.
   - **OFX**: nothing to configure. Actual uses the transaction ids to skip already imported
     transactions.
   - **CSV**: the columns `Date`, `Payee`, `Notes` and `Amount` are mapped automatically. Pick
     the date format `YYYY MM DD` if it is not detected. Actual de-duplicates CSV imports only
     by fuzzy matching on date, amount and payee.

## Supported exports

| Export | Header (excerpt) | Status |
| --- | --- | --- |
| Girokonto / Tagesgeld (new banking) | `Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;…` | ✅ |
| Kreditkarte (new banking) | `Belegdatum;Wertstellung;Status;Beschreibung;Umsatztyp;Betrag (€);…` | ✅ |
| Kreditkarte (old banking) | `…;Wertstellung;Belegdatum;Beschreibung;Betrag (EUR);…` | ✅ |

UTF-8 (with or without BOM) and Windows-1252 encoded files are accepted. If DKB changes the
format, please open an issue with an **anonymized** excerpt of the header and a row.

## Privacy

Bank exports contain sensitive data. This repository ignores `*.csv` and `*.ofx` outside of
`tests/fixtures/`, and all fixtures are synthetic. Never attach real exports to issues.

## Development

Tooling is managed with [mise](https://mise.jdx.dev/):

```sh
mise install          # python, uv, gh, prek
mise run install      # uv sync
mise run hooks        # git hooks via prek
mise run check        # lint + typecheck + tests
mise run fmt          # format and auto-fix
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).
[release-please](https://github.com/googleapis/release-please) opens release PRs from them, and
merging one publishes the package to PyPI via trusted publishing.

## License

[MIT](LICENSE)
