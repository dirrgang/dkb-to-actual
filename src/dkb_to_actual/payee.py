"""Payee and notes clean-up heuristics.

Learned from real DKB exports (see the dkb-to-ynab4 predecessor project):

* party fields are sometimes padded with a long run of spaces followed by an
  address, e.g. ``"Example S.a.r.l.<40 spaces>Example Street 1"``;
* PayPal payments only name the real merchant in the purpose text, in several
  slightly different formats, followed by boilerplate such as
  ``/ABBUCHUNG VOM PAYPAL-KONTO AWV-MELDEPFLICHT BEACHTEN …``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

_PADDED_SUFFIX = re.compile(r"\s{4,}")
_PAYPAL_STORE = re.compile(r"Ihr Einkauf bei\s+(.+?)(?:/|,|\s+AWV-MELDEPFLICHT|$)", re.IGNORECASE)
_PAYPAL_DIRECT_DEBIT = re.compile(
    r"PAYPAL-ZAHLUNG\s+UBER\s+LASTSCHRIFT\s+an\s+(.+)$", re.IGNORECASE
)
_PAYPAL_REFERENCE = re.compile(r"^(?P<reference>[A-Z]*\d+)")


def collapse_whitespace(text: str) -> str:
    """Trim and collapse internal whitespace."""
    return " ".join(text.split())


def clean_party(text: str) -> str:
    """Strip DKB's padded address suffix from a party field."""
    return collapse_whitespace(_PADDED_SUFFIX.split(text.strip(), maxsplit=1)[0])


def is_paypal(payee: str, purpose: str, reference: str = "") -> bool:
    return (
        payee.strip().lower().startswith("paypal")
        or "PAYPAL-KONTO" in purpose.upper()
        or "PP.5621.PP" in purpose.upper()
        or "PAYPAL" in reference.upper()
    )


def paypal_store(purpose: str) -> str:
    """Extract the merchant from a PayPal purpose text, or return ``""``."""
    if match := _PAYPAL_STORE.search(purpose):
        return match.group(1).strip().removeprefix(".").strip()
    if match := _PAYPAL_DIRECT_DEBIT.search(purpose):
        return match.group(1).strip()
    return ""


def paypal_reference(*values: str) -> str:
    for value in values:
        if match := _PAYPAL_REFERENCE.match(value.strip()):
            return match.group("reference")
    return ""


def normalize_details(
    payee: str, notes: str, amount: Decimal, reference: str = ""
) -> tuple[str, str]:
    """Return a cleaner ``(payee, notes)`` pair for import into Actual.

    For PayPal transactions the merchant becomes the payee and the noisy
    purpose text is replaced by a short note that keeps the PayPal reference.
    """
    payee = clean_party(payee)
    purpose = collapse_whitespace(notes)
    if not is_paypal(payee, purpose, reference):
        return payee, purpose
    if store := paypal_store(purpose):
        payee = store
    kind = "refund/credit" if amount > 0 else "purchase"
    cleaned = f"PayPal {kind}"
    if ref := paypal_reference(purpose, reference):
        cleaned = f"{cleaned}, reference {ref}"
    return collapse_whitespace(payee), cleaned
