from __future__ import annotations

import time
import datetime as dt
from dataclasses import dataclass
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class PriceSnapshot:
    prices_try: Dict[str, float]
    fetched_at: dt.datetime
    source: str
    notes: str = ""


def _to_float_tr(s: str) -> Optional[float]:
    """Converts strings like '7.609,50' to float."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None

    s = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not s or s in {".", ",", "-", "-.", "-,"}:
        return None

    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        return None


def _parse_update_date(s: str) -> dt.datetime:
    if not s:
        return dt.datetime.now()

    s = str(s).strip()
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    for f in fmts:
        try:
            return dt.datetime.strptime(s, f)
        except Exception:
            pass
    return dt.datetime.now()


def _fetch_truncgil(url: str, timeout_s: int) -> Optional[PriceSnapshot]:
    headers = {
        "User-Agent": "Mozilla/5.0 (portfolio-tracker)",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    try:
        cache_buster = int(time.time())
        sep = "&" if "?" in url else "?"
        r = requests.get(f"{url}{sep}t={cache_buster}", headers=headers, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()

        update_date = data.get("Update_Date") or data.get("UpdateDate") or data.get("update_date")
        fetched_at = _parse_update_date(update_date)

        mapping = {
            "USDTRY": "USD",
            "EURTRY": "EUR",
            "GRAM": "GRA",
            "CEYREK": "CEYREKALTIN",
            "YARIM": "YARIMALTIN",
            "ATA": "ATAALTIN",
            "BILEZIK": "YIA",
        }

        prices: Dict[str, float] = {}
        for key, trunc_key in mapping.items():
            item = data.get(trunc_key)
            buying = _to_float_tr(item.get("Buying")) if isinstance(item, dict) else None
            if buying is None:
                continue
            prices[f"{key}_BUY"] = buying
            prices[f"{key}_SELL"] = buying

        if not prices:
            return None

        return PriceSnapshot(
            prices_try=prices,
            fetched_at=fetched_at,
            source=url,
            notes="Kaynak: Truncgil today.json (Buying). Zaman: Update_Date.",
        )
    except Exception:
        return None


def fetch_from_truncgil_today_json(timeout_s: int = 10) -> Optional[PriceSnapshot]:
    url = "https://finans.truncgil.com/v4/today.json"
    return _fetch_truncgil(url, timeout_s=timeout_s)


def fetch_from_harem_gecmis_kurlar(timeout_s: int = 10) -> Optional[PriceSnapshot]:
    url = "https://www.haremaltin.com/gecmis-kurlar"
    headers = {
        "User-Agent": "Mozilla/5.0 (portfolio-tracker)",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout_s)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.find_all("tr")
        prices = {}

        for tr in rows:
            tds = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(tds) < 4:
                continue
            code = tds[0].strip().upper()
            if code in {"USDTRY", "EURTRY"}:
                buy = _to_float_tr(tds[2])
                if buy is not None:
                    prices[f"{code}_BUY"] = buy
                    prices[f"{code}_SELL"] = buy

        if not prices:
            return None

        return PriceSnapshot(
            prices_try=prices,
            fetched_at=dt.datetime.now(),
            source=url,
            notes="Fallback: Harem AltÄ±n (Buying'e yakÄ±n).",
        )
    except Exception:
        return None


def fetch_prices(timeout_s: int = 10) -> PriceSnapshot:
    sources = []
    notes = []
    merged: Dict[str, float] = {}
    fetched_at = dt.datetime.now()

    snap = fetch_from_truncgil_today_json(timeout_s=timeout_s)
    if snap:
        merged.update(snap.prices_try)
        fetched_at = snap.fetched_at
        sources.append(snap.source)
        notes.append(snap.notes)

    if not merged:
        snap2 = fetch_from_harem_gecmis_kurlar(timeout_s=timeout_s)
        if snap2:
            merged.update(snap2.prices_try)
            fetched_at = snap2.fetched_at
            sources.append(snap2.source)
            notes.append(snap2.notes)

    if not merged:
        return PriceSnapshot(
            prices_try={},
            fetched_at=fetched_at,
            source="N/A",
            notes="Fiyatlar Ã§ekilemedi. Ä°nternet/engelleme olabilir. 'Kur (TL)' alanÄ±na manuel yazabilirsin.",
        )

    return PriceSnapshot(
        prices_try=merged,
        fetched_at=fetched_at,
        source=" + ".join(sources),
        notes=" | ".join(notes),
    )
