from io import BytesIO

import pandas as pd

from app_excel import build_bilanco_xlsx


def test_build_bilanco_xlsx_creates_two_sheets():
    assets = pd.DataFrame([{"A": 1}])
    debts = pd.DataFrame([{"B": 2}])

    data = build_bilanco_xlsx(assets, debts)
    assert isinstance(data, (bytes, bytearray))

    xls = pd.ExcelFile(BytesIO(data))
    sheet_bytes = [s.encode("utf-8") for s in xls.sheet_names]
    expected_varliklar = "Varlıklar".encode("utf-8")
    expected_borclar = "Borçlar".encode("utf-8")
    assert expected_varliklar in sheet_bytes
    assert expected_borclar in sheet_bytes


def test_build_bilanco_xlsx_non_empty_bytes():
    assets = pd.DataFrame([{"A": 1}, {"A": 2}])
    debts = pd.DataFrame([{"B": 3}])

    data = build_bilanco_xlsx(assets, debts)
    assert len(data) > 100


def test_build_bilanco_xlsx_roundtrip_values():
    assets = pd.DataFrame([{"Kod": "USD", "Adet": 2.0}, {"Kod": "TRY", "Adet": 3.0}])
    debts = pd.DataFrame([{"Borc": "Kredi", "Tutar": 10.5}])

    data = build_bilanco_xlsx(assets, debts)
    xls = pd.ExcelFile(BytesIO(data))

    assets_read = pd.read_excel(xls, sheet_name="Varlıklar")
    debts_read = pd.read_excel(xls, sheet_name="Borçlar")

    assert assets_read.shape == assets.shape
    assert debts_read.shape == debts.shape
    assert assets_read.iloc[0]["Kod"] == "USD"
    assert float(debts_read.iloc[0]["Tutar"]) == 10.5


def test_build_bilanco_xlsx_handles_empty_frames():
    assets = pd.DataFrame()
    debts = pd.DataFrame()

    data = build_bilanco_xlsx(assets, debts)
    xls = pd.ExcelFile(BytesIO(data))

    assert "Varlıklar" in xls.sheet_names
    assert "Borçlar" in xls.sheet_names
