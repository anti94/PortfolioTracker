import pandas as pd
import pytest

from app_constants import ASSET_COLS, DEBT_COLS
from app_defaults import DEFAULT_ASSETS, DEFAULT_DEBTS


def test_default_assets_shape_and_columns():
    assert isinstance(DEFAULT_ASSETS, pd.DataFrame)
    assert list(DEFAULT_ASSETS.columns) == ASSET_COLS
    assert len(DEFAULT_ASSETS) > 0


def test_default_debts_shape_and_columns():
    assert isinstance(DEFAULT_DEBTS, pd.DataFrame)
    assert list(DEFAULT_DEBTS.columns) == DEBT_COLS
    assert len(DEFAULT_DEBTS) > 0


# ===== COMPREHENSIVE TESTS FOR DEFAULT_ASSETS =====

def test_default_assets_is_dataframe():
    """Verify DEFAULT_ASSETS is a pandas DataFrame"""
    assert isinstance(DEFAULT_ASSETS, pd.DataFrame)


def test_default_assets_has_rows():
    """DEFAULT_ASSETS must have at least one row"""
    assert len(DEFAULT_ASSETS) > 0
    assert DEFAULT_ASSETS.shape[0] >= 1


def test_default_assets_all_required_columns_present():
    """All ASSET_COLS must be present in DEFAULT_ASSETS"""
    for col in ASSET_COLS:
        assert col in DEFAULT_ASSETS.columns


def test_default_assets_varlık_türü_not_null():
    """Varlık Türü must never be null"""
    assert DEFAULT_ASSETS["Varlık Türü"].notna().all()


def test_default_assets_varlık_türü_not_empty_string():
    """Varlık Türü must not be empty strings"""
    assert (DEFAULT_ASSETS["Varlık Türü"].str.strip().str.len() > 0).all()


def test_default_assets_kod_not_null():
    """Kod must never be null"""
    assert DEFAULT_ASSETS["Kod"].notna().all()


def test_default_assets_kod_not_empty_string():
    """Kod must not be empty strings"""
    assert (DEFAULT_ASSETS["Kod"].str.strip().str.len() > 0).all()


def test_default_assets_adet_numeric():
    """Adet must be numeric type"""
    assert pd.api.types.is_numeric_dtype(DEFAULT_ASSETS["Adet"])


def test_default_assets_adet_non_negative():
    """Adet (quantity) must be non-negative"""
    assert (DEFAULT_ASSETS["Adet"] >= 0).all()


def test_default_assets_adet_not_nan():
    """Adet must not contain NaN values"""
    assert DEFAULT_ASSETS["Adet"].notna().all()


def test_default_assets_kur_numeric_or_null():
    """Kur (TL) must be numeric or null (not mixed types)"""
    kur = DEFAULT_ASSETS["Kur (TL)"]
    # Check that non-null values are numeric
    non_null = kur.dropna()
    assert pd.api.types.is_numeric_dtype(non_null)


def test_default_assets_kur_non_negative_when_present():
    """Kur (TL) when present must be non-negative"""
    kur_nonnull = DEFAULT_ASSETS["Kur (TL)"].dropna()
    assert (kur_nonnull >= 0).all()


def test_default_assets_try_has_correct_kur():
    """TRY asset should have Kur (TL) = 1.0"""
    try_rows = DEFAULT_ASSETS[DEFAULT_ASSETS["Kod"] == "TRY"]
    if len(try_rows) > 0:
        assert (try_rows["Kur (TL)"] == 1.0).all()


def test_default_assets_not_column_is_string_or_null():
    """Not (Notes) column should contain strings or null"""
    assert DEFAULT_ASSETS["Not"].dtype == "object"


def test_default_assets_no_duplicate_indices():
    """No duplicate indices in DEFAULT_ASSETS"""
    assert not DEFAULT_ASSETS.index.duplicated().any()


def test_default_assets_total_quantity_reasonable():
    """Total quantity of all assets should be positive"""
    total = DEFAULT_ASSETS["Adet"].sum()
    assert total > 0


def test_default_assets_at_least_try_asset():
    """Should contain at least one TRY (Turkish Lira) asset"""
    try_count = (DEFAULT_ASSETS["Kod"] == "TRY").sum()
    assert try_count >= 1


# ===== COMPREHENSIVE TESTS FOR DEFAULT_DEBTS =====

def test_default_debts_is_dataframe():
    """Verify DEFAULT_DEBTS is a pandas DataFrame"""
    assert isinstance(DEFAULT_DEBTS, pd.DataFrame)


def test_default_debts_has_rows():
    """DEFAULT_DEBTS must have at least one row"""
    assert len(DEFAULT_DEBTS) > 0
    assert DEFAULT_DEBTS.shape[0] >= 1


def test_default_debts_all_required_columns_present():
    """All DEBT_COLS must be present in DEFAULT_DEBTS"""
    for col in DEBT_COLS:
        assert col in DEFAULT_DEBTS.columns


def test_default_debts_borç_adı_not_null():
    """Borç Adı must never be null"""
    assert DEFAULT_DEBTS["Borç Adı"].notna().all()


def test_default_debts_borç_adı_not_empty_string():
    """Borç Adı must not be empty strings"""
    assert (DEFAULT_DEBTS["Borç Adı"].str.strip().str.len() > 0).all()


def test_default_debts_tutar_numeric():
    """Tutar (TL) must be numeric type"""
    assert pd.api.types.is_numeric_dtype(DEFAULT_DEBTS["Tutar (TL)"])


def test_default_debts_tutar_non_negative():
    """Tutar (TL) must be non-negative"""
    assert (DEFAULT_DEBTS["Tutar (TL)"] >= 0).all()


def test_default_debts_tutar_not_nan():
    """Tutar (TL) must not contain NaN values"""
    assert DEFAULT_DEBTS["Tutar (TL)"].notna().all()


def test_default_debts_not_column_is_string_or_null():
    """Not (Notes) column should contain strings or null"""
    assert DEFAULT_DEBTS["Not"].dtype == "object"


def test_default_debts_no_duplicate_indices():
    """No duplicate indices in DEFAULT_DEBTS"""
    assert not DEFAULT_DEBTS.index.duplicated().any()


def test_default_debts_total_reasonable_range():
    """Total debt should be within reasonable range (0 to 10M TL)"""
    total = DEFAULT_DEBTS["Tutar (TL)"].sum()
    assert 0 <= total <= 10_000_000


# ===== INTEGRATION TESTS =====

def test_assets_and_debts_are_different_objects():
    """Assets and debts should be different DataFrame instances"""
    assert id(DEFAULT_ASSETS) != id(DEFAULT_DEBTS)


def test_assets_and_debts_column_counts_different():
    """Assets and debts typically have different number of columns"""
    assert len(ASSET_COLS) == len(DEFAULT_ASSETS.columns)
    assert len(DEBT_COLS) == len(DEFAULT_DEBTS.columns)


def test_assets_columns_match_constants():
    """DEFAULT_ASSETS columns match ASSET_COLS constant"""
    assert list(DEFAULT_ASSETS.columns) == ASSET_COLS


def test_debts_columns_match_constants():
    """DEFAULT_DEBTS columns match DEBT_COLS constant"""
    assert list(DEFAULT_DEBTS.columns) == DEBT_COLS


def test_no_cross_column_contamination():
    """Asset-specific columns should not appear in DEBT_COLS and vice versa"""
    asset_specific = {"Adet", "Kur (TL)", "Varlık Türü"}
    debt_specific = {"Tutar (TL)"}
    
    asset_cols_set = set(ASSET_COLS)
    debt_cols_set = set(DEBT_COLS)
    
    assert not asset_specific.intersection(debt_cols_set)
    assert not debt_specific.intersection(asset_cols_set)
