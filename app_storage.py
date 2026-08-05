from __future__ import annotations

import json
import os
import datetime as dt
import tempfile
from typing import Any, Dict, Optional

import streamlit as st

from app_mongo import get_db, get_db_if_available, mongo_available

PERSISTED_STATE_SIG_KEY = "_persisted_state_sig"

def load_state_from_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_state_to_json(path: str, session_state: Dict[str, Any]) -> bool:
    data = build_payload_from_session(session_state)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


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


def _payload_signature(payload: Dict[str, Any]) -> str:
    comparable = dict(payload)
    comparable.pop("saved_at", None)
    return json.dumps(comparable, ensure_ascii=False, sort_keys=True)


def mark_payload_saved(
    session_state: Dict[str, Any],
    payload: Dict[str, Any],
    state_key: str = PERSISTED_STATE_SIG_KEY,
) -> None:
    session_state[state_key] = _payload_signature(payload)


def mark_current_state_saved(
    session_state: Dict[str, Any],
    state_key: str = PERSISTED_STATE_SIG_KEY,
) -> None:
    mark_payload_saved(session_state, build_payload_from_session(session_state), state_key=state_key)


def load_state_for_user(username: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if mongo_available():
        db = get_db_if_available()
        if db is None:
            return None
        doc = db["user_state"].find_one({"username": username}, {"_id": 0})
        if not doc:
            return None
        return doc.get("payload")
    if not path:
        return None
    return load_state_from_json(path)


def save_state_for_user(username: str, session_state: Dict[str, Any], path: Optional[str] = None) -> bool:
    payload = build_payload_from_session(session_state)
    return save_payload_for_user(username, payload, path=path)


def save_payload_for_user(username: str, payload: Dict[str, Any], path: Optional[str] = None) -> bool:
    if mongo_available():
        db = get_db_if_available()
        if db is None:
            return False
        db["user_state"].update_one(
            {"username": username},
            {"$set": {"username": username, "payload": payload, "updated_at": dt.datetime.utcnow()}},
            upsert=True,
        )
        return True
    if not path:
        return False
    return save_state(path, payload)


def save_state_for_user_if_changed(
    username: str,
    session_state: Dict[str, Any],
    path: Optional[str] = None,
    state_key: str = PERSISTED_STATE_SIG_KEY,
) -> bool:
    payload = build_payload_from_session(session_state)
    signature = _payload_signature(payload)
    if session_state.get(state_key) == signature:
        return False
    if save_payload_for_user(username, payload, path=path):
        session_state[state_key] = signature
        return True
    return False


def load_state(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        st.warning(f"State dosyasÄ± okunamadÄ±: {e}")
        return {}


def save_state(path: str, payload: dict) -> bool:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

    fd = None
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix=f"{os.path.basename(path)}.",
            suffix=".tmp",
            dir=directory or None,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        fd = None
        os.replace(temp_path, path)
        return True
    except Exception as e:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        st.error(f"State kaydedilemedi: {e}")
        return False
