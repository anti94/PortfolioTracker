from __future__ import annotations

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app_auth import hash_password  # noqa: E402
from app_mongo import get_db, get_mongo_db_name, get_mongo_uri  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset Mongo users and seed a single admin user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    if not get_mongo_uri():
        print("MONGO_URI is not set.", file=sys.stderr)
        return 2

    db = get_db()

    # Wipe collections
    db["users"].delete_many({})
    db["user_state"].delete_many({})

    salt_b64, hash_b64 = hash_password(args.password)
    db["users"].insert_one(
        {
            "username": args.username,
            "salt": salt_b64,
            "hash": hash_b64,
            "role": "admin",
        }
    )

    print(f"OK. Reset users in DB '{get_mongo_db_name()}'. Admin: {args.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
