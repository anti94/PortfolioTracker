import pandas as pd

from app_compute import compute_display_assets, compute_totals, get_auto_unit_price


def test_get_auto_unit_price_try_is_one():
    assert get_auto_unit_price("TRY", {}, "BUY") == 1.0


def test_get_auto_unit_price_unknown_returns_none():
    assert get_auto_unit_price("UNKNOWN", {}, "BUY") is None


def test_get_auto_unit_price_sell_uses_sell_key():
    prices = {"USDTRY_SELL": 31.0, "USDTRY_BUY": 30.0}
    assert get_auto_unit_price("USD", prices, "SELL") == 31.0


def test_get_auto_unit_price_code_normalization():
    prices = {"EURTRY_BUY": 35.0}
    assert get_auto_unit_price(" eur ", prices, "BUY") == 35.0


def test_compute_display_assets_uses_manual_when_no_auto():
    assets = pd.DataFrame([{"Kod": "TRY", "Adet": 2.0, "Kur (TL)": 5.0}])
    display = compute_display_assets(assets, {}, use_side="BUY")
    assert display["Kur (TL)"].tolist() == [1.0]
    assert display["Tutar (TL)"].tolist() == [2.0]


def test_compute_display_assets_manual_kur_used_if_auto_missing():
    assets = pd.DataFrame([{"Kod": "XYZ", "Adet": 3.0, "Kur (TL)": 4.0}])
    display = compute_display_assets(assets, {}, use_side="BUY")
    assert display["Kur (TL)"].tolist() == [4.0]
    assert display["Tutar (TL)"].tolist() == [12.0]


def test_compute_display_assets_invalid_values_safe_zero():
    assets = pd.DataFrame([{"Kod": "XYZ", "Adet": "bad", "Kur (TL)": "nope"}])
    display = compute_display_assets(assets, {}, use_side="BUY")
    assert display["Tutar (TL)"].tolist() == [0.0]


def test_compute_totals_missing_columns_returns_zero():
    assets = pd.DataFrame([{"Kod": "TRY"}])
    debts = pd.DataFrame([{"Borç Adı": "Test"}])
    total_assets, total_debts, net = compute_totals(assets, debts)
    assert total_assets == 0.0
    assert total_debts == 0.0
    assert net == 0.0


def test_compute_display_assets_and_totals():
    assets = pd.DataFrame(
        [
            {"Kod": "USD", "Adet": 2.0, "Kur (TL)": None},
            {"Kod": "TRY", "Adet": 3.0, "Kur (TL)": 1.0},
        ]
    )
    prices = {"USDTRY_BUY": 30.0}

    display = compute_display_assets(assets, prices, use_side="BUY")
    assert display["Tutar (TL)"].tolist() == [60.0, 3.0]

    debts = pd.DataFrame([{"Tutar (TL)": 10.0}])
    total_assets, total_debts, net = compute_totals(display, debts)
    assert total_assets == 63.0
    assert total_debts == 10.0
    assert net == 53.0
