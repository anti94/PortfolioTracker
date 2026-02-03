from __future__ import annotations

from typing import Dict, Optional, Tuple

import pandas as pd

from app_constants import AUTO_PRICE_KEY


def get_auto_unit_price(code: str, prices: Dict[str, float], use_side: str) -> Optional[float]:
    code = str(code or "").strip().upper()
    if code == "TRY":
        return 1.0
    pair = AUTO_PRICE_KEY.get(code)
    if not pair:
        return None
    buy_key, sell_key = pair
    key = sell_key if use_side == "SELL" else buy_key
    return prices.get(key)


def compute_display_assets(assets_df: pd.DataFrame, prices: Dict[str, float], use_side: str) -> pd.DataFrame:
    df = assets_df.copy()
    kur_list = []
    tutar_list = []

    for _, row in df.iterrows():
        code = row.get("Kod", "")
        qty = row.get("Adet", 0.0)
        manual_kur = row.get("Kur (TL)", None)

        auto_kur = get_auto_unit_price(code, prices, use_side)
        kur = auto_kur if auto_kur is not None else manual_kur

        kur_list.append(kur)

        try:
            q = float(qty) if qty is not None else 0.0
            k = float(kur) if kur is not None else 0.0
            tutar_list.append(q * k)
        except Exception:
            tutar_list.append(0.0)

    df["Kur (TL)"] = kur_list
    df["Tutar (TL)"] = tutar_list
    return df


def compute_totals(assets_display: pd.DataFrame, debts_df: pd.DataFrame) -> Tuple[float, float, float]:
    total_assets = float(assets_display["Tutar (TL)"].fillna(0).sum()) if "Tutar (TL)" in assets_display.columns else 0.0
    total_debts = float(debts_df["Tutar (TL)"].fillna(0).sum()) if "Tutar (TL)" in debts_df.columns else 0.0
    return total_assets, total_debts, total_assets - total_debts
