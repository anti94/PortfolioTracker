from __future__ import annotations

import time
import datetime as dt
import re
import unicodedata
import json
from dataclasses import dataclass
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

try:
    import cloudscraper  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    cloudscraper = None


@dataclass
class PriceSnapshot:
    prices_try: Dict[str, float]
    fetched_at: dt.datetime
    source: str
    notes: str = ""
    raw_data: Optional[Dict[str, object]] = None
    update_date_str: Optional[str] = None


def _to_float_tr(s: str) -> Optional[float]:
    """Converts strings like '7.609,50' to float."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        try:
            return float(s)
        except Exception:
            return None
    s = str(s).strip()
    if not s:
        return None

    s = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not s or s in {".", ",", "-", "-.", "-,"}:
        return None

    # 50.578 -> 50578 (dot as thousands separator)
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    elif "." in s and "," in s:
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

        mapping_candidates = {
            "USD": ["USD", "USDTRY", "DOLAR", "DOLARTL"],
            "EUR": ["EUR", "EURTRY", "EURO", "EUROTL"],
            "GRAM": ["GRAM", "GRA", "GRAMALTIN"],
            "CEYREK": ["CEYREK", "CEYREKALTIN"],
            "YARIM": ["YARIM", "YARIMALTIN"],
            "ATA": ["ATA", "ATAALTIN"],
            "BILEZIK": ["BILEZIK", "YIA", "BILEZIKALTIN"],
        }

        def find_item(candidates: list[str]) -> Optional[dict]:
            for key in candidates:
                if key in data and isinstance(data.get(key), dict):
                    return data.get(key)
            # Fallback: contains match
            candidates_lower = [c.lower() for c in candidates]
            for k, v in data.items():
                if not isinstance(v, dict):
                    continue
                kl = str(k).lower()
                if any(c in kl for c in candidates_lower):
                    return v
            return None

        def extract_buy_sell(item: dict) -> tuple[Optional[float], Optional[float]]:
            # Try common key variants (case-insensitive, Turkish variants)
            keys = {str(k).strip().lower(): v for k, v in item.items()}
            buy_keys = ["buying", "buy", "alis", "alış", "alisfiyati", "alışfiyati", "fiyat"]
            sell_keys = ["selling", "sell", "satis", "satış", "satisfiyati", "satışfiyati"]
            buying = None
            selling = None
            for k in buy_keys:
                if k in keys:
                    buying = _to_float_tr(keys[k])
                    break
            for k in sell_keys:
                if k in keys:
                    selling = _to_float_tr(keys[k])
                    break
            return buying, selling

        prices: Dict[str, float] = {}
        for code, candidates in mapping_candidates.items():
            item = find_item(candidates)
            if not isinstance(item, dict):
                continue
            buying, selling = extract_buy_sell(item)
            if buying is None:
                continue
            prices[f"{code}_BUY"] = buying
            prices[f"{code}_SELL"] = selling if selling is not None else buying

        if not prices:
            return None

        return PriceSnapshot(
            prices_try=prices,
            fetched_at=fetched_at,
            source=url,
            notes="Kaynak: Truncgil today.json. Zaman: Update_Date.",
            raw_data=data,
            update_date_str=str(update_date) if update_date else None,
        )
    except Exception:
        return None


def fetch_from_truncgil_today_json(timeout_s: int = 10) -> Optional[PriceSnapshot]:
    url = "https://finans.truncgil.com/v4/today.json"
    return _fetch_truncgil(url, timeout_s=timeout_s)


def fetch_from_harem_gecmis_kurlar(timeout_s: int = 10) -> Optional[PriceSnapshot]:
    url = "https://www.haremaltin.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (portfolio-tracker)",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    try:
        r = _http_get_with_fallback(url, headers=headers, timeout_s=timeout_s)
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
                    key = "USD" if code == "USDTRY" else "EUR"
                    prices[f"{key}_BUY"] = buy
                    prices[f"{key}_SELL"] = buy

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


def _extract_first_prices(text: str) -> tuple[Optional[float], Optional[float]]:
    if not text:
        return None, None
    pattern = r"\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?|\d+(?:,\d+)?"
    vals = []
    for m in re.findall(pattern, text):
        v = _to_float_tr(m)
        # TRY gold quotes are typically high enough; ignore day/month style numbers.
        if v is not None and v > 100:
            vals.append(v)
    if not vals:
        return None, None
    buy = vals[0]
    sell = vals[1] if len(vals) > 1 else vals[0]
    return buy, sell




def _normalize_text_tr(s: str) -> str:
    if not s:
        return ""
    s = str(s).translate(str.maketrans(
        "çğıöşüÇĞİÖŞÜ",
        "cgiosuCGIOSU",
    ))
    s = s.replace("ı", "i").replace("İ", "I")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def _map_harem_name_to_code(name_text: str) -> Optional[str]:
    n = _normalize_text_tr(name_text)
    if "gram" in n:
        return "GRAM"
    if "eski ceyrek" in n or "ceyrek" in n:
        return "CEYREK"
    if "eski yarim" in n or "yarim" in n:
        return "YARIM"
    if any(x in n for x in ["eski ata", "ata altin", "tam altin", "cumhuriyet altini", "ata5"]):
        return "ATA"
    if "22 ayar" in n or "bilezik" in n:
        return "BILEZIK"
    return None


def _looks_like_bot_block(text: str) -> bool:
    t = _normalize_text_tr(text or "")
    markers = [
        "just a moment",
        "enable javascript",
        "verify you are human",
        "cloudflare",
        "cf-chl",
        "access denied",
        "bot",
    ]
    return any(m in t for m in markers)


def _http_get_with_fallback(url: str, headers: dict, timeout_s: int):
    r = requests.get(url, headers=headers, timeout=timeout_s)
    if r.status_code < 400 and not _looks_like_bot_block(r.text):
        return r
    if cloudscraper is None:
        return r
    try:
        scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
        cr = scraper.get(url, headers=headers, timeout=timeout_s)
        return cr
    except Exception:
        return r


def _extract_prices_from_harem_json(data: object) -> Dict[str, float]:
    prices: Dict[str, float] = {}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            keys_norm = {_normalize_text_tr(str(k)): v for k, v in node.items()}
            name = (
                keys_norm.get("name")
                or keys_norm.get("ad")
                or keys_norm.get("title")
                or keys_norm.get("label")
                or keys_norm.get("isim")
                or keys_norm.get("urun")
                or keys_norm.get("symbol")
                or keys_norm.get("code")
                or keys_norm.get("kod")
            )
            code = _map_harem_name_to_code(str(name)) if name is not None else None
            if not code:
                for v in node.values():
                    if isinstance(v, str):
                        code = _map_harem_name_to_code(v)
                        if code:
                            break

            buy = None
            sell = None
            buy_keys = ["alis", "buy", "buying", "alisfiyati", "alis_fiyati", "fiyat", "price", "a"]
            sell_keys = ["satis", "sell", "selling", "satisfiyati", "satis_fiyati", "s"]
            for k, v in keys_norm.items():
                if buy is None and any(bk in k for bk in buy_keys):
                    buy = _to_float_tr(v)
                if sell is None and any(sk in k for sk in sell_keys):
                    sell = _to_float_tr(v)

            if code and buy is not None and buy > 100:
                prices[f"{code}_BUY"] = buy
                prices[f"{code}_SELL"] = sell if (sell is not None and sell > 100) else buy

            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return prices


def fetch_from_harem_homepage(timeout_s: int = 10) -> Optional[PriceSnapshot]:
    url = "https://www.haremaltin.com/"
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
        prices: Dict[str, float] = {}

        aliases = {
            "GRAM": ["gram altin", "gram"],
            "CEYREK": ["eski ceyrek", "ceyrek altin", "ceyrek"],
            "YARIM": ["eski yarim", "yarim altin", "yarim"],
            "ATA": ["eski ata", "ata altin", "tam altin", "cumhuriyet altini", "ata5"],
            "BILEZIK": ["22 ayar", "22 ayar bilezik", "bilezik"],
        }
        aliases = {k: [_normalize_text_tr(x) for x in v] for k, v in aliases.items()}

        # Pass-1: visible DOM cards/rows.
        all_nodes = soup.find_all(True)
        for code, names in aliases.items():
            for node in all_nodes:
                if node.name in {"html", "body"}:
                    continue
                txt = node.get_text(" ", strip=True)
                if not txt:
                    continue
                normalized = _normalize_text_tr(txt)
                if not any(name in normalized for name in names):
                    continue
                buy, sell = _extract_first_prices(txt)
                if buy is None and node.parent is not None and node.parent.name not in {"html", "body"}:
                    parent_txt = node.parent.get_text(" ", strip=True)
                    buy, sell = _extract_first_prices(parent_txt)
                if buy is not None:
                    prices[f"{code}_BUY"] = buy
                    prices[f"{code}_SELL"] = sell if sell is not None else buy
                    break

        # Pass-2: inline content search (html/script text).
        html_normalized = _normalize_text_tr(r.text)
        for code, names in aliases.items():
            if f"{code}_BUY" in prices:
                continue
            for name in names:
                idx = html_normalized.find(name)
                if idx < 0:
                    continue
                start_idx = max(0, idx - 300)
                end_idx = min(len(r.text), idx + 560)
                snippet = r.text[start_idx:end_idx]
                buy, sell = _extract_first_prices(snippet)
                if buy is not None:
                    prices[f"{code}_BUY"] = buy
                    prices[f"{code}_SELL"] = sell if sell is not None else buy
                    break

        # Pass-3: discover likely AJAX/JSON endpoints from HTML and parse structured payloads.
        if len(prices) < 3:
            candidate_urls = set()
            for tag in soup.find_all("script", src=True):
                src = str(tag.get("src") or "").strip()
                if not src:
                    continue
                candidate_urls.add(urljoin(url, src))

            for m in re.finditer(r"[\"']((?:https?:)?//[^\"']+|/[^\"']+)[\"']", r.text):
                raw = m.group(1)
                low = raw.lower()
                if not any(k in low for k in ["api", "ajax", "json", "fiyat", "kur", "gold", "altin"]):
                    continue
                if raw.startswith("//"):
                    raw = "https:" + raw
                candidate_urls.add(urljoin(url, raw))

            api_headers = dict(headers)
            api_headers["Referer"] = url
            api_headers["X-Requested-With"] = "XMLHttpRequest"

            for c_url in list(candidate_urls)[:16]:
                c_low = c_url.lower()
                if "haremaltin.com" not in c_low:
                    continue
                try:
                    cr = _http_get_with_fallback(c_url, headers=api_headers, timeout_s=max(3, timeout_s))
                    if cr.status_code >= 400:
                        continue

                    payload = None
                    ctype = str(cr.headers.get("content-type") or "").lower()
                    text = cr.text or ""
                    is_jsonish = "json" in ctype or text.lstrip().startswith("{") or text.lstrip().startswith("[")

                    if is_jsonish:
                        try:
                            payload = cr.json()
                        except Exception:
                            # Some endpoints return JS with JSON embedded.
                            mobj = re.search(r'(\{.*\}|\[.*\])', text, flags=re.S)
                            if mobj:
                                try:
                                    payload = json.loads(mobj.group(1))
                                except Exception:
                                    payload = None

                    if payload is not None:
                        found = _extract_prices_from_harem_json(payload)
                        for k, v in found.items():
                            prices.setdefault(k, v)

                    # Text fallback on endpoint response.
                    if len(prices) < 3 and text:
                        t_norm = _normalize_text_tr(text)
                        for code, names in aliases.items():
                            if f"{code}_BUY" in prices:
                                continue
                            for name in names:
                                idx = t_norm.find(name)
                                if idx < 0:
                                    continue
                                sidx = max(0, idx - 220)
                                eidx = min(len(text), idx + 420)
                                buy, sell = _extract_first_prices(text[sidx:eidx])
                                if buy is not None:
                                    prices[f"{code}_BUY"] = buy
                                    prices[f"{code}_SELL"] = sell if sell is not None else buy
                                    break
                except Exception:
                    continue

        if not prices:
            return None

        return PriceSnapshot(
            prices_try=prices,
            fetched_at=dt.datetime.now(),
            source=url,
            notes="Kaynak: Harem Altin homepage/ajax scrape.",
        )
    except Exception:
        return None


def fetch_prices(timeout_s: int = 10, source_preference: str = "auto") -> PriceSnapshot:
    sources = []
    notes = []
    merged: Dict[str, float] = {}
    fetched_at = dt.datetime.now()
    raw_data = None
    update_date_str = None

    pref = str(source_preference or "auto").strip().lower()
    if pref == "truncgil":
        fetchers = [fetch_from_truncgil_today_json]
    elif pref == "harem":
        fetchers = [fetch_from_harem_homepage]
    else:
        fetchers = [fetch_from_truncgil_today_json, fetch_from_harem_homepage]

    for fetcher in fetchers:
        snap = fetcher(timeout_s=timeout_s)
        if not snap:
            continue
        merged.update(snap.prices_try)
        fetched_at = snap.fetched_at
        sources.append(snap.source)
        notes.append(snap.notes)
        if snap.raw_data:
            raw_data = snap.raw_data
            update_date_str = snap.update_date_str
        # In auto mode we stop after first successful source.
        if pref == "auto":
            break

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
        raw_data=raw_data,
        update_date_str=update_date_str,
    )
