from __future__ import annotations

from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"
OFFENSE_PRF = DATA_DIR / "TST-OFF1.prf"
OFFENSE2_PRF = DATA_DIR / "TST-OFF2.prf"
DEFENSE_PRF = DATA_DIR / "TST-DEF1.prf"
DEFENSE2_PRF = DATA_DIR / "TST-DEF2.prf"


@pytest.fixture
def offense_prf() -> Path:
    return OFFENSE_PRF


@pytest.fixture
def offense2_prf() -> Path:
    return OFFENSE2_PRF


@pytest.fixture
def defense_prf() -> Path:
    return DEFENSE_PRF


@pytest.fixture
def defense2_prf() -> Path:
    return DEFENSE2_PRF
