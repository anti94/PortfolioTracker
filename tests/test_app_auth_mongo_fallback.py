from __future__ import annotations

import app_auth
import app_mongo


class _BrokenDb:
    def command(self, name: str):
        raise RuntimeError("mongo unavailable")

    def __getitem__(self, name: str):
        return self

    def find_one(self, *args, **kwargs):
        raise RuntimeError("mongo unavailable")


def test_get_db_if_available_clears_stale_cached_connection(monkeypatch):
    app_mongo._client = object()
    app_mongo._db = _BrokenDb()
    monkeypatch.setattr(app_mongo, "get_mongo_uri", lambda: None)

    assert app_mongo.get_db_if_available() is None
    assert app_mongo._client is None
    assert app_mongo._db is None


def test_get_user_role_falls_back_to_local_users_when_mongo_query_fails(monkeypatch):
    monkeypatch.setattr(app_auth, "get_db_if_available", lambda: _BrokenDb())
    users_data = {"users": {"cgulucan": {"role": "admin"}}}

    assert app_auth.get_user_role(users_data, "cgulucan") == "admin"
