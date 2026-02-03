import json

import pandas as pd

from app_storage import load_state, load_state_from_json, save_state, save_state_to_json


def test_save_and_load_state_json_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    session_state = {
        "assets_df": pd.DataFrame([{"A": 1}]),
        "debts_df": pd.DataFrame([{"B": 2}]),
        "cashflow_base_date": "2026-01-28",
    }

    save_state_to_json(str(path), session_state)
    data = load_state_from_json(str(path))

    assert data is not None
    assert "assets" in data
    assert "debts" in data
    assert data["cashflow_base_date"] == "2026-01-28"


def test_load_state_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "nope.json"
    assert load_state(str(missing)) == {}


def test_save_state_writes_file(tmp_path):
    path = tmp_path / "legacy.json"
    payload = {"x": 1, "y": [1, 2, 3]}

    save_state(str(path), payload)
    assert path.exists()

    content = json.loads(path.read_text(encoding="utf-8"))
    assert content == payload
