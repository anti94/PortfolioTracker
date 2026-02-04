from __future__ import annotations

import os
from typing import Optional


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


def get_db():
    global _client, _db
    if _db is not None:
        return _db
    uri = get_mongo_uri()
    if not uri:
        raise RuntimeError("MongoDB URI not configured")
    from pymongo import MongoClient

    _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    _db = _client[get_mongo_db_name()]
    try:
        _db["users"].create_index("username", unique=True)
        _db["user_state"].create_index("username", unique=True)
    except Exception:
        # Index creation can fail if permissions are limited; ignore to avoid crash
        pass
    return _db
