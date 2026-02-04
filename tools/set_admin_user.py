from __future__ import annotations

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app_mongo import get_db, get_mongo_uri  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Set a user as admin in MongoDB.")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()

    if not get_mongo_uri():
        print("MONGO_URI is not set.", file=sys.stderr)
        return 2

    db = get_db()
    result = db["users"].update_one(
        {"username": args.username},
        {"$set": {"role": "admin"}},
        upsert=False,
    )

    if result.matched_count == 0:
        print("User not found.", file=sys.stderr)
        return 3

    print(f"OK. User '{args.username}' is now admin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
