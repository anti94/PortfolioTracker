import re
from datetime import datetime

import pytest

from app_constants import (
    APP_TITLE,
    AUTO_PRICE_KEY,
    ASSET_COLS,
    BASELINE_DATE,
    BASELINE_NET,
    DEBT_COLS,
    DEFAULT_STATE_FILE,
    STATE_FILE,
)


def test_constants_basic_values():
    assert STATE_FILE == DEFAULT_STATE_FILE
    assert APP_TITLE == "Portfolio Tracker"
    assert BASELINE_DATE == "2026-01-28"
    assert BASELINE_NET == 2_000_000.0
    assert "USD" in AUTO_PRICE_KEY
    assert AUTO_PRICE_KEY["USD"][0].endswith("_BUY")


def test_columns_types_and_contents():
    assert isinstance(ASSET_COLS, list)
    assert isinstance(DEBT_COLS, list)
    assert all(isinstance(x, str) for x in ASSET_COLS)
    assert all(isinstance(x, str) for x in DEBT_COLS)
    # common expected column names (may vary by locale)
    assert len(ASSET_COLS) >= 1
    assert len(DEBT_COLS) >= 1
    assert len(set(ASSET_COLS)) == len(ASSET_COLS)  # no duplicates


def test_auto_price_key_structure_and_naming():
    assert isinstance(AUTO_PRICE_KEY, dict)
    assert len(AUTO_PRICE_KEY) > 0
    for key, pair in AUTO_PRICE_KEY.items():
        assert isinstance(key, str)
        assert key.isupper()
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        buy, sell = pair
        assert isinstance(buy, str) and isinstance(sell, str)
        assert buy.endswith("_BUY")
        assert sell.endswith("_SELL")
        # values often include the currency code as prefix
        assert buy.startswith(key) or key in buy


def test_baseline_date_is_valid_iso_date():
    assert isinstance(BASELINE_DATE, str)
    datetime.strptime(BASELINE_DATE, "%Y-%m-%d")


def test_baseline_net_and_app_title():
    assert isinstance(BASELINE_NET, (int, float))
    assert BASELINE_NET >= 0
    assert APP_TITLE and isinstance(APP_TITLE, str)
    assert "Portfolio" in APP_TITLE or "portfolio" in APP_TITLE


def test_state_file_defaults_and_format():
    assert STATE_FILE == DEFAULT_STATE_FILE
    assert STATE_FILE.endswith(".json")
    assert "/" not in STATE_FILE and "\\" not in STATE_FILE  # simple filename, not a path


def test_auto_price_keys_cover_expected_units():
    for unit in ("USD", "EUR", "GRAM"):
        assert unit in AUTO_PRICE_KEY
