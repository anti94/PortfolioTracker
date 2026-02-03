import datetime as dt

from app_pricing import (
    PriceSnapshot,
    _parse_update_date,
    _to_float_tr,
    fetch_prices,
)


def test_to_float_tr_handles_tr_format():
    assert _to_float_tr("7.609,50") == 7609.50
    assert _to_float_tr("1,25") == 1.25
    assert _to_float_tr("") is None


def test_parse_update_date_formats():
    parsed = _parse_update_date("2026-02-01 12:34:56")
    assert isinstance(parsed, dt.datetime)
    assert parsed.year == 2026
    assert parsed.month == 2
    assert parsed.day == 1


def test_fetch_prices_prefers_truncgil(monkeypatch):
    snap = PriceSnapshot(
        prices_try={"USDTRY_BUY": 30.0},
        fetched_at=dt.datetime(2026, 2, 1, 10, 0, 0),
        source="mock",
        notes="mock",
    )

    monkeypatch.setattr("app_pricing.fetch_from_truncgil_today_json", lambda timeout_s=10: snap)
    monkeypatch.setattr("app_pricing.fetch_from_harem_gecmis_kurlar", lambda timeout_s=10: None)

    result = fetch_prices(timeout_s=1)
    assert result.prices_try["USDTRY_BUY"] == 30.0
    assert result.source == "mock"


def test_fetch_prices_fallbacks_when_primary_empty(monkeypatch):
    snap = PriceSnapshot(
        prices_try={"EURTRY_BUY": 35.0},
        fetched_at=dt.datetime(2026, 2, 1, 10, 0, 0),
        source="fallback",
        notes="fallback",
    )

    monkeypatch.setattr("app_pricing.fetch_from_truncgil_today_json", lambda timeout_s=10: None)
    monkeypatch.setattr("app_pricing.fetch_from_harem_gecmis_kurlar", lambda timeout_s=10: snap)

    result = fetch_prices(timeout_s=1)
    assert result.prices_try["EURTRY_BUY"] == 35.0
    assert "fallback" in result.source


def test_fetch_prices_returns_empty_when_all_fail(monkeypatch):
    monkeypatch.setattr("app_pricing.fetch_from_truncgil_today_json", lambda timeout_s=10: None)
    monkeypatch.setattr("app_pricing.fetch_from_harem_gecmis_kurlar", lambda timeout_s=10: None)

    result = fetch_prices(timeout_s=1)
    assert result.prices_try == {}
