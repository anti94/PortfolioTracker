import datetime as dt

from app_pricing import (
    PriceSnapshot,
    _parse_update_date,
    _to_float_tr,
    fetch_from_harem_homepage,
    fetch_prices,
)


def test_to_float_tr_handles_tr_format():
    assert _to_float_tr("7.609,50") == 7609.50
    assert _to_float_tr("1,25") == 1.25
    assert _to_float_tr("50.578") == 50578.0
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
    monkeypatch.setattr("app_pricing.fetch_from_harem_homepage", lambda timeout_s=10: None)

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
    monkeypatch.setattr("app_pricing.fetch_from_harem_homepage", lambda timeout_s=10: snap)

    result = fetch_prices(timeout_s=1)
    assert result.prices_try["EURTRY_BUY"] == 35.0
    assert "fallback" in result.source


def test_fetch_prices_returns_empty_when_all_fail(monkeypatch):
    monkeypatch.setattr("app_pricing.fetch_from_truncgil_today_json", lambda timeout_s=10: None)
    monkeypatch.setattr("app_pricing.fetch_from_harem_homepage", lambda timeout_s=10: None)

    result = fetch_prices(timeout_s=1)
    assert result.prices_try == {}


def test_fetch_prices_uses_selected_source(monkeypatch):
    truncgil_snap = PriceSnapshot(
        prices_try={"USD_BUY": 30.0},
        fetched_at=dt.datetime(2026, 2, 1, 10, 0, 0),
        source="truncgil",
        notes="truncgil",
    )
    harem_snap = PriceSnapshot(
        prices_try={"GRAM_BUY": 3500.0},
        fetched_at=dt.datetime(2026, 2, 1, 10, 0, 0),
        source="harem",
        notes="harem",
    )

    monkeypatch.setattr("app_pricing.fetch_from_truncgil_today_json", lambda timeout_s=10: truncgil_snap)
    monkeypatch.setattr("app_pricing.fetch_from_harem_homepage", lambda timeout_s=10: harem_snap)

    result = fetch_prices(timeout_s=1, source_preference="harem")
    assert result.source == "harem"
    assert result.prices_try == {"GRAM_BUY": 3500.0}


def test_fetch_from_harem_homepage_parses_gold_units(monkeypatch):
    class DummyResp:
        status_code = 200
        text = """
        <html><body>
          <div>Gram Altın Alış 3.743,92 Satış 3.760,00</div>
          <div>Çeyrek Altın Alış 11.883,52 Satış 11.950,00</div>
          <div>Yarım Altın Alış 23.692,77 Satış 23.850,00</div>
          <div>Ata Altın Alış 49.019,52 Satış 49.350,00</div>
          <div>22 Ayar Bilezik Alış 6.773,61 Satış 6.900,00</div>
        </body></html>
        """

        def raise_for_status(self):
            return None

    monkeypatch.setattr("app_pricing.requests.get", lambda *args, **kwargs: DummyResp())
    snap = fetch_from_harem_homepage(timeout_s=1)
    assert snap is not None
    assert snap.prices_try["GRAM_BUY"] == 3743.92
    assert snap.prices_try["CEYREK_BUY"] == 11883.52
    assert snap.prices_try["YARIM_BUY"] == 23692.77
    assert snap.prices_try["ATA_BUY"] == 49019.52
    assert snap.prices_try["BILEZIK_BUY"] == 6773.61
