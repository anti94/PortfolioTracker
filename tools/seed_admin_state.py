from __future__ import annotations

import os
import sys
import datetime as dt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app_mongo import get_db, get_mongo_uri  # noqa: E402


USERNAME = "cgulucan"

ASSETS = [
    {
        "Varlık Türü": "Mevduat Hesabı",
        "Kod": "TRY",
        "Adet": 90083.4,
        "Kur (TL)": 1.0,
        "Yıllık Faiz (%)": 41.0,
        "Not": "",
    },
    {
        "Varlık Türü": "Euro",
        "Kod": "EUR",
        "Adet": 600.0,
        "Kur (TL)": 51.3117,
        "Yıllık Faiz (%)": 0.0,
        "Not": "",
    },
    {
        "Varlık Türü": "Dolar",
        "Kod": "USD",
        "Adet": 0.0,
        "Kur (TL)": 43.4748,
        "Yıllık Faiz (%)": 0.0,
        "Not": "",
    },
    {
        "Varlık Türü": "Ata Altın",
        "Kod": "ATA",
        "Adet": 26.0,
        "Kur (TL)": 48620.0400,
        "Yıllık Faiz (%)": 0.0,
        "Not": "",
    },
    {
        "Varlık Türü": "22-ayar-bilezik",
        "Kod": "BILEZIK",
        "Adet": 50.0,
        "Kur (TL)": 6718.4100,
        "Yıllık Faiz (%)": 0.0,
        "Not": "",
    },
    {
        "Varlık Türü": "Gram Altın",
        "Kod": "GRAM",
        "Adet": 4.5,
        "Kur (TL)": 6877.6100,
        "Yıllık Faiz (%)": 0.0,
        "Not": "",
    },
    {
        "Varlık Türü": "Çeyrek",
        "Kod": "CEYREK",
        "Adet": 8.0,
        "Kur (TL)": 11786.6800,
        "Yıllık Faiz (%)": 0.0,
        "Not": "",
    },
    {
        "Varlık Türü": "Yarım",
        "Kod": "YARIM",
        "Adet": 1.0,
        "Kur (TL)": 23499.6900,
        "Yıllık Faiz (%)": 0.0,
        "Not": "",
    },
]

DEBTS = [
    {
        "Borç Adı": "",
        "Tutar (TL)": 0.0,
        "Not": "",
    }
]


def main() -> int:
    if not get_mongo_uri():
        print("MONGO_URI is not set.", file=sys.stderr)
        return 2

    payload = {
        "assets": ASSETS,
        "debts": DEBTS,
        "net_history": [],
        "cashflow_base_date": dt.date.today().isoformat(),
        "baseline_date": dt.date.today().isoformat(),
        "baseline_net": 0.0,
        "interest_last_date": dt.date.today().isoformat(),
        "saved_at": dt.datetime.now().replace(microsecond=0).isoformat(),
    }

    db = get_db()
    db["user_state"].update_one(
        {"username": USERNAME},
        {"$set": {"username": USERNAME, "payload": payload, "updated_at": dt.datetime.utcnow()}},
        upsert=True,
    )

    print(f"OK. Seeded state for {USERNAME}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
