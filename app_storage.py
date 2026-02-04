from __future__ import annotations

import json
import os
import datetime as dt
from typing import Any, Dict, Optional

import streamlit as st

from app_mongo import get_db, mongo_enabled

def load_state_from_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_state_to_json(path: str, session_state: Dict[str, Any]) -> None:
    data = build_payload_from_session(session_state)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_payload_from_session(session_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "assets": session_state["assets_df"].to_dict(orient="records"),
        "debts": session_state["debts_df"].to_dict(orient="records"),
        "net_history": session_state.get("net_history", []),
        "cashflow_base_date": session_state.get("cashflow_base_date"),
        "baseline_date": session_state.get("baseline_date"),
        "baseline_net": session_state.get("baseline_net"),
        "interest_last_date": session_state.get("interest_last_date"),
        "saved_at": dt.datetime.now().replace(microsecond=0).isoformat(),
    }


def load_state_for_user(username: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if mongo_enabled():
        db = get_db()
        doc = db["user_state"].find_one({"username": username}, {"_id": 0})
        if not doc:
            return None
        return doc.get("payload")
    if not path:
        return None
    return load_state_from_json(path)


def save_state_for_user(username: str, session_state: Dict[str, Any], path: Optional[str] = None) -> None:
    payload = build_payload_from_session(session_state)
    save_payload_for_user(username, payload, path=path)


def save_payload_for_user(username: str, payload: Dict[str, Any], path: Optional[str] = None) -> None:
    if mongo_enabled():
        db = get_db()
        db["user_state"].update_one(
            {"username": username},
            {"$set": {"username": username, "payload": payload, "updated_at": dt.datetime.utcnow()}},
            upsert=True,
        )
        return
    if not path:
        return
    save_state(path, payload)


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
