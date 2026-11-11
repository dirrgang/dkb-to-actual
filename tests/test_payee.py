from __future__ import annotations

from decimal import Decimal

import pytest

from dkb_to_actual.payee import clean_party, collapse_whitespace, normalize_details, paypal_store


def test_collapse_whitespace() -> None:
    assert collapse_whitespace("  A   B  ") == "A B"


def test_clean_party_strips_padded_address() -> None:
    padded = "Example Marketplace S.a.r.l." + " " * 40 + "Example Street 1"
    assert clean_party(padded) == "Example Marketplace S.a.r.l."


def test_clean_party_keeps_ordinary_spacing() -> None:
    assert clean_party("Foo  Bar GmbH") == "Foo Bar GmbH"


@pytest.mark.parametrize(
    ("purpose", "store"),
    [
        ("foo, Ihr Einkauf bei Store Name, bar", "Store Name"),
        ("foo, Ihr Einkauf bei Store Name/ABBUCHUNG VOM PAYPAL-KONTO", "Store Name"),
        ("foo, Ihr Einkauf bei Example Shop Ltd.", "Example Shop Ltd."),
        (
            "1000000000000/PP.5621.PP/. PAYPAL-ZAHLUNG UBER LASTSCHRIFT an recipient.example",
            "recipient.example",
        ),
        ("1000000000000/PP.5621.PP/. , Ihr Einkauf bei", ""),
        ("", ""),
    ],
)
def test_paypal_store(purpose: str, store: str) -> None:
    assert paypal_store(purpose) == store


def test_paypal_purchase() -> None:
    assert normalize_details(
        "PayPal Europe S.a.r.l. et Cie S.C.A",
        "1000000000001/PP.5621.PP/. Example Store GmbH, Ihr Einkauf bei Example Store GmbH",
        Decimal("-24.98"),
    ) == ("Example Store GmbH", "PayPal purchase, reference 1000000000001")


def test_paypal_refund_with_boilerplate() -> None:
    assert normalize_details(
        "PayPal Europe S.a.r.l. et Cie S.C.A",
        ". Example Retail GmbH . Co. KG, Ihr Einkauf bei Example Retail GmbH . Co. KG/ABBUCHUNG "
        "VOM PAYPAL-KONTO AWV-MELDEPFLICHT BEACHTEN HOTLINE BUNDESBANK (0800) 1234-111",
        Decimal("158.69"),
    ) == ("Example Retail GmbH . Co. KG", "PayPal refund/credit")


def test_paypal_alternate_format_with_reference_column() -> None:
    assert normalize_details(
        "PayPal (Europe) S.a r.l. et Cie, S.C.A.",
        "1000000000002 PP.5621.PP . Example Food UG, Ihr Einkauf bei Example Food UG",
        Decimal("-9.00"),
        "1000000000002 PP.5621.PP PAYPAL",
    ) == ("Example Food UG", "PayPal purchase, reference 1000000000002")


def test_paypal_without_purpose_keeps_payee() -> None:
    assert normalize_details(
        "PayPal (Europe) S.a r.l. et Cie, S.C.A.",
        "",
        Decimal("-87.05"),
        "1000000000003 PP.5621.PP PAYPAL",
    ) == ("PayPal (Europe) S.a r.l. et Cie, S.C.A.", "PayPal purchase, reference 1000000000003")


def test_non_paypal_is_untouched() -> None:
    assert normalize_details("REWE Markt GmbH", "  1234   5678 ", Decimal("-1")) == (
        "REWE Markt GmbH",
        "1234 5678",
    )
