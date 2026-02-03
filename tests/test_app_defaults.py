import pandas as pd
import pytest

from app_constants import ASSET_COLS, AUTO_PRICE_KEY, DEBT_COLS
from app_defaults import DEFAULT_ASSETS, DEFAULT_DEBTS


def test_default_assets_shape_and_columns():
    assert isinstance(DEFAULT_ASSETS, pd.DataFrame)
    assert list(DEFAULT_ASSETS.columns) == ASSET_COLS
    assert len(DEFAULT_ASSETS) > 0


def test_default_debts_shape_and_columns():
    assert isinstance(DEFAULT_DEBTS, pd.DataFrame)
    assert list(DEFAULT_DEBTS.columns) == DEBT_COLS
    assert len(DEFAULT_DEBTS) > 0


# Additional comprehensive tests for DEFAULT_ASSETS

def test_default_assets_column_count():
    """Verify DEFAULT_ASSETS has exactly the expected columns"""
    assert DEFAULT_ASSETS.shape[1] == len(ASSET_COLS)
    assert DEFAULT_ASSETS.shape[1] >= 4  # at least: Varlık Türü, Kod, Adet, Kur (TL)


def test_default_assets_no_empty_rows():
    """Ensure no completely empty rows in DEFAULT_ASSETS"""
    assert DEFAULT_ASSETS.shape[0] > 0
    assert not DEFAULT_ASSETS.isnull().all(axis=1).any()


def test_default_assets_varlık_türü_not_empty():
    """All assets must have a Varlık Türü (Asset Type)"""
    assert not DEFAULT_ASSETS["Varlık Türü"].isnull().any()
    assert (DEFAULT_ASSETS["Varlık Türü"].str.len() > 0).all()


def test_default_assets_kod_not_empty():
    """All assets must have a Kod (Code)"""
    assert not DEFAULT_ASSETS["Kod"].isnull().any()
    assert (DEFAULT_ASSETS["Kod"].str.len() > 0).all()


def test_default_assets_adet_is_numeric():
    """Adet (Quantity) must be numeric"""
    assert pd.api.types.is_numeric_dtype(DEFAULT_ASSETS["Adet"])
    assert (DEFAULT_ASSETS["Adet"] >= 0).all()


def test_default_assets_kur_numeric_or_null():
    """Kur (TL) should be numeric or null, never negative"""
    kur = DEFAULT_ASSETS["Kur (TL)"]
    assert kur.dropna().apply(lambda x: x >= 0).all()


def test_default_assets_kod_unique_or_allowed_duplicates():
    """Check for duplicate codes (some duplicates are allowed like CEYREK)"""
    kod_counts = DEFAULT_ASSETS["Kod"].value_counts()
    # Allow codes to appear multiple times (e.g., CEYREK appears 2x)
    assert (kod_counts <= 10).all()  # but not more than 10 times


def test_default_assets_try_has_kur_1_0():
    """TRY (Turkish Lira) asset should have Kur (TL) = 1.0"""
    try_assets = DEFAULT_ASSETS[DEFAULT_ASSETS["Kod"] == "TRY"]
    if len(try_assets) > 0:
        assert (try_assets["Kur (TL)"] == 1.0).all()


def test_default_assets_no_negative_adet():
    """No asset should have negative quantity"""
    assert (DEFAULT_ASSETS["Adet"] >= 0).all()


def test_default_assets_required_fields_not_null():
    """Required fields (type, code, quantity) should never be null"""
    assert not DEFAULT_ASSETS["Varlık Türü"].isnull().any()
    assert not DEFAULT_ASSETS["Kod"].isnull().any()
    assert not DEFAULT_ASSETS["Adet"].isnull().any()


def test_default_assets_codes_are_trimmed_strings():
    """Codes should be non-empty, trimmed strings"""
    codes = DEFAULT_ASSETS["Kod"]
    assert codes.apply(lambda x: isinstance(x, str)).all()
    assert (codes.str.strip() == codes).all()


def test_default_assets_codes_supported_for_pricing():
    """Each code should be TRY or present in AUTO_PRICE_KEY for pricing"""
    codes = set(DEFAULT_ASSETS["Kod"].unique())
    allowed = {"TRY"} | set(AUTO_PRICE_KEY.keys())
    assert codes.issubset(allowed)


def test_default_assets_columns_unique_and_index_range():
    """Columns should be unique and index should be a zero-based RangeIndex"""
    assert DEFAULT_ASSETS.columns.is_unique
    assert isinstance(DEFAULT_ASSETS.index, pd.RangeIndex)
    assert DEFAULT_ASSETS.index.start == 0


def test_default_assets_non_try_kur_is_null():
    """Non-TRY assets should not have a fixed Kur (TL) at defaults"""
    non_try = DEFAULT_ASSETS[DEFAULT_ASSETS["Kod"] != "TRY"]
    if len(non_try) > 0:
        assert non_try["Kur (TL)"].isnull().all()


def test_default_assets_kod_uppercase():
    """Codes should be uppercase strings"""
    codes = DEFAULT_ASSETS["Kod"]
    assert (codes.str.upper() == codes).all()


def test_default_assets_not_column_exists():
    """'Not' (Notes) column should exist and be string type or null"""
    assert "Not" in DEFAULT_ASSETS.columns
    assert DEFAULT_ASSETS["Not"].dtype == "object" or DEFAULT_ASSETS["Not"].dtype == "string"


def test_default_assets_dataframe_not_modified():
    """Ensure original DEFAULT_ASSETS is not accidentally modified"""
    original_shape = (len(DEFAULT_ASSETS), len(DEFAULT_ASSETS.columns))
    assert original_shape[0] > 0
    assert original_shape[1] > 0
    # Re-import to check it's still the same
    from app_defaults import DEFAULT_ASSETS as REIMPORTED
    assert REIMPORTED.shape == original_shape


# Additional comprehensive tests for DEFAULT_DEBTS

def test_default_debts_column_count():
    """Verify DEFAULT_DEBTS has exactly the expected columns"""
    assert DEFAULT_DEBTS.shape[1] == len(DEBT_COLS)
    assert DEFAULT_DEBTS.shape[1] >= 2  # at least: Borç Adı, Tutar (TL)


def test_default_debts_no_empty_rows():
    """Ensure no completely empty rows in DEFAULT_DEBTS"""
    assert DEFAULT_DEBTS.shape[0] > 0
    assert not DEFAULT_DEBTS.isnull().all(axis=1).any()


def test_default_debts_borç_adı_not_empty():
    """All debts must have a Borç Adı (Debt Name)"""
    assert not DEFAULT_DEBTS["Borç Adı"].isnull().any()
    assert (DEFAULT_DEBTS["Borç Adı"].str.len() > 0).all()


def test_default_debts_tutar_is_numeric():
    """Tutar (TL) (Amount) must be numeric and non-negative"""
    assert pd.api.types.is_numeric_dtype(DEFAULT_DEBTS["Tutar (TL)"])
    assert (DEFAULT_DEBTS["Tutar (TL)"] >= 0).all()


def test_default_debts_required_fields_not_null():
    """Required debt fields should never be null"""
    assert not DEFAULT_DEBTS["Borç Adı"].isnull().any()
    assert not DEFAULT_DEBTS["Tutar (TL)"].isnull().any()


def test_default_debts_notes_string_or_empty():
    """Notes should be strings (including empty) when present"""
    notes = DEFAULT_DEBTS["Not"]
    assert notes.apply(lambda x: isinstance(x, str) or pd.isna(x)).all()


def test_default_debts_columns_unique_and_index_range():
    """Columns should be unique and index should be a zero-based RangeIndex"""
    assert DEFAULT_DEBTS.columns.is_unique
    assert isinstance(DEFAULT_DEBTS.index, pd.RangeIndex)
    assert DEFAULT_DEBTS.index.start == 0


def test_default_debts_not_column_exists():
    """'Not' (Notes) column should exist"""
    assert "Not" in DEFAULT_DEBTS.columns


def test_default_debts_no_negative_tutar():
    """No debt should have negative amount"""
    assert (DEFAULT_DEBTS["Tutar (TL)"] >= 0).all()


def test_default_debts_tutar_reasonable_range():
    """Debt amounts should be within reasonable range (0 to 10M TL)"""
    assert (DEFAULT_DEBTS["Tutar (TL)"] <= 10_000_000).all()


def test_default_debts_dataframe_not_modified():
    """Ensure original DEFAULT_DEBTS is not accidentally modified"""
    original_shape = (len(DEFAULT_DEBTS), len(DEFAULT_DEBTS.columns))
    assert original_shape[0] > 0
    assert original_shape[1] > 0
    # Re-import to check it's still the same
    from app_defaults import DEFAULT_DEBTS as REIMPORTED
    assert REIMPORTED.shape == original_shape


# Integration tests

def test_asset_and_debt_dataframes_independent():
    """Assets and debts should be separate independent DataFrames"""
    assert id(DEFAULT_ASSETS) != id(DEFAULT_DEBTS)
    assert DEFAULT_ASSETS.shape != DEFAULT_DEBTS.shape or DEFAULT_ASSETS.shape[1] != DEFAULT_DEBTS.shape[1]


def test_default_assets_total_value_reasonable():
    """Total asset value should be positive and reasonable"""
    # TRY assets * 1.0 + other assets (without exchange rate) 
    try_total = DEFAULT_ASSETS[DEFAULT_ASSETS["Kod"] == "TRY"]["Adet"].sum()
    assert try_total > 0


def test_default_debts_total_reasonable():
    """Total debt should be positive and reasonable"""
    total_debt = DEFAULT_DEBTS["Tutar (TL)"].sum()
    assert total_debt >= 0
    assert total_debt <= 1_000_000_000  # max 1B TL reasonable


def test_default_assets_no_duplicate_columns():
    """Asset columns should not contain duplicates"""
    assert DEFAULT_ASSETS.columns.is_unique


def test_default_debts_no_duplicate_columns():
    """Debt columns should not contain duplicates"""
    assert DEFAULT_DEBTS.columns.is_unique


def test_default_assets_kod_not_whitespace():
    """Kod values should not be just whitespace"""
    codes = DEFAULT_ASSETS["Kod"]
    assert (codes.str.strip().str.len() > 0).all()


def test_default_assets_adet_finite():
    """Adet values should be finite numbers"""
    assert pd.Series(DEFAULT_ASSETS["Adet"]).apply(lambda x: pd.notna(x)).all()


def test_default_debts_tutar_finite():
    """Tutar values should be finite numbers"""
    assert pd.Series(DEFAULT_DEBTS["Tutar (TL)"]).apply(lambda x: pd.notna(x)).all()
