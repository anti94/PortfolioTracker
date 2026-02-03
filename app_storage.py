from __future__ import annotations

import json
import os
import datetime as dt
from typing import Any, Dict, Optional

import streamlit as st


def load_state_from_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_state_to_json(path: str, session_state: Dict[str, Any]) -> None:
    data = {
        "assets": session_state["assets_df"].to_dict(orient="records"),
        "debts": session_state["debts_df"].to_dict(orient="records"),
        "cashflow_base_date": session_state.get("cashflow_base_date"),
        "saved_at": dt.datetime.now().replace(microsecond=0).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_state(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        st.warning(f"State dosyasÄ± okunamadÄ±: {e}")
        return {}


def save_state(path: str, payload: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"State kaydedilemedi: {e}")
