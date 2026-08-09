"""Migrate file-based users and portfolio state into MongoDB.

Unlike tools/reset_users_mongo.py, this does NOT delete anything: every user in
users.json and every user_data/<username>/state.json is upserted, so the local
files remain the source of truth until the migration is verified.

Usage:
    set MONGO_URI=mongodb+srv://...
    python tools/migrate_to_mongo.py --dry-run     # preview, no writes
    python tools/migrate_to_mongo.py               # perform the migration
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app_mongo import get_db, get_mongo_db_name, get_mongo_uri  # noqa: E402

USERS_PATH = os.path.join(APP_DIR, "users.json")
USER_DATA_ROOT = os.path.join(APP_DIR, "user_data")

# Keys app_storage.build_payload_from_session writes; anything else in a
# state.json file is ignored so a stale key can't leak into Mongo.
PAYLOAD_KEYS = (
    "assets",
    "debts",
    "net_history",
    "cashflow_base_date",
    "baseline_date",
    "baseline_net",
    "interest_last_date",
    "saved_at",
)


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"  ! {path} okunamadi: {exc}", file=sys.stderr)
        return None


def _collect_users() -> dict:
    data = _read_json(USERS_PATH) or {}
    users = data.get("users")
    return users if isinstance(users, dict) else {}


def _collect_states() -> dict:
    states = {}
    if not os.path.isdir(USER_DATA_ROOT):
        return states
    for name in sorted(os.listdir(USER_DATA_ROOT)):
        state_file = os.path.join(USER_DATA_ROOT, name, "state.json")
        if not os.path.isfile(state_file):
            continue
        payload = _read_json(state_file)
        if not isinstance(payload, dict):
            continue
        states[name] = {k: payload[k] for k in PAYLOAD_KEYS if k in payload}
    return states


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate users.json + user_data/*/state.json into MongoDB.")
    parser.add_argument("--dry-run", action="store_true", help="Sadece ne yapilacagini goster, yazma.")
    args = parser.parse_args()

    if not get_mongo_uri():
        print("MONGO_URI tanimli degil.", file=sys.stderr)
        return 2

    users = _collect_users()
    states = _collect_states()

    print(f"users.json         : {len(users)} kullanici")
    print(f"user_data/*/state  : {len(states)} portfoy")
    for username in sorted(users):
        role = users[username].get("role", "user")
        has_state = "state var" if username in states else "state YOK"
        print(f"  - {username:<14} rol={role:<6} {has_state}")
    orphans = sorted(set(states) - set(users))
    for username in orphans:
        print(f"  - {username:<14} (users.json'da yok, state yine de tasinacak)")

    if args.dry_run:
        print("\n--dry-run: hicbir sey yazilmadi.")
        return 0

    if not users and not states:
        print("Tasinacak veri yok.", file=sys.stderr)
        return 1

    db = get_db()
    print(f"\nMongoDB'ye baglanildi (db={get_mongo_db_name()}). Yaziliyor...")

    user_count = 0
    for username, rec in users.items():
        salt, hash_ = rec.get("salt"), rec.get("hash")
        if not salt or not hash_:
            print(f"  ! {username}: salt/hash eksik, atlandi", file=sys.stderr)
            continue
        role = rec.get("role", "user")
        db["users"].update_one(
            {"username": username},
            {"$set": {"username": username, "salt": salt, "hash": hash_,
                      "role": role if role in ("admin", "user") else "user"}},
            upsert=True,
        )
        user_count += 1

    state_count = 0
    for username, payload in states.items():
        db["user_state"].update_one(
            {"username": username},
            {"$set": {"username": username, "payload": payload,
                      "updated_at": dt.datetime.utcnow()}},
            upsert=True,
        )
        state_count += 1

    print(f"OK. {user_count} kullanici, {state_count} portfoy tasindi.")
    print(f"Dogrulama: users={db['users'].count_documents({})}, "
          f"user_state={db['user_state'].count_documents({})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
