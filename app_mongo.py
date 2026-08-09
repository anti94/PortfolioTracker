from __future__ import annotations

import os
import re
from typing import Any, Optional


def _get_secret(name: str) -> Optional[str]:
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def get_mongo_uri() -> Optional[str]:
    uri = os.getenv("MONGO_URI") or _get_secret("MONGO_URI")
    if not uri:
        return None
    uri = str(uri).strip()
    # Strip surrounding quotes if env/secret includes them
    if (uri.startswith('"') and uri.endswith('"')) or (uri.startswith("'") and uri.endswith("'")):
        uri = uri[1:-1].strip()
    return uri or None


def get_mongo_db_name() -> str:
    name = os.getenv("MONGO_DB") or _get_secret("MONGO_DB") or "portfolio"
    name = str(name).strip()
    if (name.startswith('"') and name.endswith('"')) or (name.startswith("'") and name.endswith("'")):
        name = name[1:-1].strip()
    return name or "portfolio"


def mongo_enabled() -> bool:
    return bool(get_mongo_uri())


_client = None
_db = None
_last_error: Optional[str] = None


def _reset_cached_connection() -> None:
    global _client, _db
    _client = None
    _db = None


def _mask_credentials(text: str) -> str:
    # Connection errors can echo the URI back; never surface user:pass.
    return re.sub(r"://[^:/@\s]+:[^@\s]+@", "://***:***@", str(text))


def get_last_error() -> Optional[str]:
    """Why the last connection attempt failed, or None if it succeeded."""
    return _last_error


def get_db():
    global _client, _db
    if _db is not None:
        try:
            _db.command("ping")
            return _db
        except Exception:
            _reset_cached_connection()
    uri = get_mongo_uri()
    if not uri:
        raise RuntimeError("MongoDB URI not configured")
    from pymongo import MongoClient

    _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    _db = _client[get_mongo_db_name()]
    _db.command("ping")
    try:
        _db["users"].create_index("username", unique=True)
        _db["user_state"].create_index("username", unique=True)
    except Exception:
        # Index creation can fail if permissions are limited; ignore to avoid crash
        pass
    return _db


def get_db_if_available() -> Optional[Any]:
    global _last_error
    try:
        db = get_db()
        _last_error = None
        return db
    except Exception as exc:
        _last_error = _mask_credentials(f"{type(exc).__name__}: {exc}")
        _reset_cached_connection()
        return None


def mongo_available() -> bool:
    return get_db_if_available() is not None
