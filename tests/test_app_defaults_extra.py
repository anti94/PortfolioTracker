import pandas as pd

from app_constants import ASSET_COLS, DEBT_COLS
from app_defaults import DEFAULT_ASSETS, DEFAULT_DEBTS


def test_assets_columns_match_constants_order():
    assert list(DEFAULT_ASSETS.columns) == ASSET_COLS


def test_debts_columns_match_constants_order():
    assert list(DEFAULT_DEBTS.columns) == DEBT_COLS


def test_assets_asset_type_strings_nonempty():
    asset_types = DEFAULT_ASSETS["Varlık Türü"]
    assert asset_types.apply(lambda x: isinstance(x, str)).all()
    assert (asset_types.str.strip().str.len() > 0).all()


def test_assets_codes_nonempty_strings():
    codes = DEFAULT_ASSETS["Kod"]
    assert codes.apply(lambda x: isinstance(x, str)).all()
    assert (codes.str.strip().str.len() > 0).all()


def test_assets_adet_numeric_dtype():
    assert pd.api.types.is_numeric_dtype(DEFAULT_ASSETS["Adet"])


def test_assets_kur_non_negative_when_present():
    kur = DEFAULT_ASSETS["Kur (TL)"].dropna()
    assert (kur >= 0).all()


def test_debts_name_strings_nonempty():
    names = DEFAULT_DEBTS["Borç Adı"]
    assert names.apply(lambda x: isinstance(x, str)).all()
    assert (names.str.strip().str.len() > 0).all()


def test_debts_tutar_numeric_dtype():
    assert pd.api.types.is_numeric_dtype(DEFAULT_DEBTS["Tutar (TL)"])
