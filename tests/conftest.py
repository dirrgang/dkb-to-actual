from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def giro_csv() -> Path:
    return FIXTURES / "giro.csv"


@pytest.fixture
def credit_csv() -> Path:
    return FIXTURES / "credit.csv"


@pytest.fixture
def credit_legacy_csv() -> Path:
    return FIXTURES / "credit_legacy.csv"
