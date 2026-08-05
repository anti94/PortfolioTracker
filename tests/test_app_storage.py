import json

import pandas as pd

from app_storage import (
    PERSISTED_STATE_SIG_KEY,
    load_state,
    load_state_from_json,
    mark_current_state_saved,
    save_state,
    save_state_for_user_if_changed,
    save_state_to_json,
)


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


def test_save_state_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "legacy.json"
    payload = {"ok": True}

    save_state(str(path), payload)

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_save_state_for_user_if_changed_skips_unchanged_payload(monkeypatch):
    calls = []
    session_state = {
        "assets_df": pd.DataFrame([{"A": 1}]),
        "debts_df": pd.DataFrame([{"B": 2}]),
        "net_history": [{"date": "2026-08-05", "net": 10}],
        "cashflow_base_date": "2026-08-05",
        "baseline_date": "2026-08-05",
        "baseline_net": 10,
        "interest_last_date": "2026-08-05",
    }

    def fake_save_payload_for_user(username, payload, path=None):
        calls.append((username, payload, path))
        return True

    monkeypatch.setattr("app_storage.save_payload_for_user", fake_save_payload_for_user)

    assert save_state_for_user_if_changed("cgulucan", session_state, path="state.json") is True
    assert save_state_for_user_if_changed("cgulucan", session_state, path="state.json") is False
    assert len(calls) == 1
    assert session_state[PERSISTED_STATE_SIG_KEY]


def test_mark_current_state_saved_allows_saved_at_to_change_without_resave(monkeypatch):
    calls = []
    session_state = {
        "assets_df": pd.DataFrame([{"A": 1}]),
        "debts_df": pd.DataFrame([{"B": 2}]),
        "net_history": [],
        "cashflow_base_date": "2026-08-05",
        "baseline_date": "2026-08-05",
        "baseline_net": 10,
        "interest_last_date": "2026-08-05",
    }

    def fake_save_payload_for_user(username, payload, path=None):
        calls.append((username, payload, path))
        return True

    monkeypatch.setattr("app_storage.save_payload_for_user", fake_save_payload_for_user)

    mark_current_state_saved(session_state)
    assert save_state_for_user_if_changed("cgulucan", session_state, path="state.json") is False
    assert calls == []
