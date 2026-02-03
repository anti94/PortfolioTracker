from __future__ import annotations

from typing import Dict, List, Optional

from app_constants import BASELINE_DATE, BASELINE_NET


def ensure_baseline_net(session_state: Dict) -> None:
    nh: List[dict] = session_state.get("net_history", [])
    baseline_date = session_state.get("baseline_date", BASELINE_DATE)
    baseline_net = session_state.get("baseline_net", BASELINE_NET)
    if not any(r.get("date") == baseline_date for r in nh):
        nh.append({"date": baseline_date, "net": baseline_net})
        nh.sort(key=lambda x: x.get("date", ""))
        session_state["net_history"] = nh


def upsert_net_snapshot(session_state: Dict, date_str: str, net_value: float) -> None:
    nh: List[dict] = session_state.get("net_history", [])
    found = False
    for r in nh:
        if r.get("date") == date_str:
            r["net"] = float(net_value)
            found = True
            break
    if not found:
        nh.append({"date": date_str, "net": float(net_value)})
    nh.sort(key=lambda x: x.get("date", ""))
    session_state["net_history"] = nh


def get_net_for(session_state: Dict, date_str: str) -> Optional[float]:
    nh: List[dict] = session_state.get("net_history", [])
    for r in nh:
        if r.get("date") == date_str:
            try:
                return float(r.get("net"))
            except Exception:
                return None
    return None
