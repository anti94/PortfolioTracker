from __future__ import annotations

import time
import datetime as dt

import pandas as pd
import streamlit as st

from app_compute import compute_display_assets, compute_totals
from app_constants import APP_TITLE, ASSET_COLS, DEBT_COLS, DEFAULT_STATE_FILE, STATE_FILE
from app_defaults import DEFAULT_ASSETS, DEFAULT_DEBTS
from app_excel import build_bilanco_xlsx
from app_net_history import ensure_baseline_net, get_net_for, upsert_net_snapshot
from app_pricing import PriceSnapshot, fetch_prices
from app_storage import load_state_from_json, save_state, save_state_to_json


# ----------------------------
# UI
# ----------------------------


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# Sidebar controls FIRST (so reruns see flags)
st.sidebar.header("Ayarlar")
state_path = st.sidebar.text_input("Kayıt dosyası", value=DEFAULT_STATE_FILE)
refresh_sec = st.sidebar.number_input("Oto yenileme (sn) — 0 kapalı", min_value=0, max_value=3600, value=60, step=10)
use_side = st.sidebar.selectbox(
    "Fiyat türü",
    options=["BUY", "SELL"],
    index=0,
    help="Bu sürüm BUY (Buying) kullanır. SELL de aynı değere eşit tutuluyor."
)
timeout_s = st.sidebar.slider("Fiyat çekme timeout (sn)", min_value=3, max_value=30, value=10)

# --- Nonce for cache busting (important)
st.session_state.setdefault("prices_nonce", 0)

st.sidebar.divider()
if st.sidebar.button("Fiyatları Güncelle"):
    # Force bypass cache: bump nonce + clear cache + set flag
    st.session_state["prices_nonce"] += 1
    st.session_state["force_refresh_prices"] = True
    try:
        cached_prices.clear()
    except Exception:
        pass

if st.sidebar.button("Bilanço Son Durumu Json'dan Yükle"):
    st.session_state["force_reload_state"] = True
if st.sidebar.button("Bilançoyu Kaydet"):
    st.session_state["force_save_state"] = True


# =========================
# Force Load / Save handlers
# =========================
if st.session_state.get("force_reload_state"):
    data = load_state_from_json(STATE_FILE)
    if data:
        assets = pd.DataFrame(data.get("assets", []))
        debts  = pd.DataFrame(data.get("debts", []))

        # kolon fix
        for c in ASSET_COLS:
            if c not in assets.columns:
                assets[c] = "" if c in ("Varlık Türü", "Kod", "Not") else 0.0
        assets = assets[ASSET_COLS]

        for c in DEBT_COLS:
            if c not in debts.columns:
                debts[c] = "" if c in ("Borç Adı", "Not") else 0.0
        debts = debts[DEBT_COLS]

        st.session_state["assets_df"] = assets
        st.session_state["debts_df"] = debts
        st.session_state["cashflow_base_date"] = data.get(
            "cashflow_base_date",
            st.session_state.get("cashflow_base_date", dt.date.today().isoformat())
        )

        st.sidebar.success("Bilanço Durumun JSON'dan yüklendi.")
    else:
        st.sidebar.warning("JSON bulunamadı / okunamadı.")

    st.session_state["force_reload_state"] = False
    st.rerun()

if st.session_state.get("force_save_state"):
    save_state_to_json(STATE_FILE, st.session_state)
    st.sidebar.success("Bilanço Durumu JSON'a kaydedildi.")
    st.session_state["force_save_state"] = False


st.sidebar.divider()

# =========================
# Init session (FROM JSON)
# =========================
if "initialized" not in st.session_state:
    data = load_state_from_json(STATE_FILE)

    if data:
        assets = pd.DataFrame(data.get("assets", []))
        debts  = pd.DataFrame(data.get("debts", []))
        st.session_state["cashflow_base_date"] = data.get("cashflow_base_date", dt.date.today().isoformat())
    else:
        assets = DEFAULT_ASSETS.copy()
        debts  = DEFAULT_DEBTS.copy()
        st.session_state["cashflow_base_date"] = dt.date.today().isoformat()

    # kolonları garanti altına al
    for c in ASSET_COLS:
        if c not in assets.columns:
            assets[c] = "" if c in ("Varlık Türü", "Kod", "Not") else 0.0
    assets = assets[ASSET_COLS]

    for c in DEBT_COLS:
        if c not in debts.columns:
            debts[c] = "" if c in ("Borç Adı", "Not") else 0.0
    debts = debts[DEBT_COLS]

    st.session_state["assets_df"] = assets
    st.session_state["debts_df"]  = debts

    st.session_state.setdefault("prices_snap", PriceSnapshot(prices_try={}, fetched_at=dt.datetime.now(), source="N/A"))
    st.session_state.setdefault("net_history", [])
    st.session_state.setdefault("force_reload_state", False)
    st.session_state.setdefault("force_save_state", False)

    st.session_state["initialized"] = True


st.session_state.setdefault("prices_snap", PriceSnapshot(prices_try={}, fetched_at=dt.datetime.now(), source="N/A"))
st.session_state.setdefault("net_history", [])
st.session_state.setdefault("cashflow_base_date", "2026-01-28")  # varsayılan baseline


@st.cache_data(ttl=60)
def cached_prices(timeout_s_: int, nonce: int) -> PriceSnapshot:
    # nonce intentionally unused except to change the cache key
    _ = nonce
    return fetch_prices(timeout_s=timeout_s_)


# Auto refresh tick
do_refresh = st.session_state.get("force_refresh_prices", False)
if refresh_sec and refresh_sec > 0:
    st.caption(f"Oto yenileme açık: {refresh_sec} sn")
    st.session_state["_last_tick"] = st.session_state.get("_last_tick", time.time())
    if time.time() - st.session_state["_last_tick"] >= refresh_sec:
        do_refresh = True
        st.session_state["_last_tick"] = time.time()
        st.session_state["prices_nonce"] += 1  # bump nonce so cached_prices can't stick

if do_refresh:
    # Always pull live
    snap = fetch_prices(timeout_s=timeout_s)
    st.session_state["prices_snap"] = snap
    st.session_state["force_refresh_prices"] = False
else:
    # Cached pull
    snap = cached_prices(timeout_s_=timeout_s, nonce=st.session_state["prices_nonce"])
    st.session_state["prices_snap"] = snap

snap: PriceSnapshot = st.session_state["prices_snap"]


# ----------------------------
# Assets table
# ----------------------------

st.subheader("Varlıklar")
st.caption("Kod: TRY, USD, EUR, GRAM, CEYREK, YARIM, ATA, BILEZIK. 'Tutar (TL)' otomatik = Kur * Adet.")

display_df_assets = compute_display_assets(
    st.session_state["assets_df"],
    snap.prices_try,
    use_side=use_side
)

assets_col, _empty = st.columns([1, 1])   # %50 tablo, %50 boş
with assets_col:
    edited_assets = st.data_editor(
        display_df_assets,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Adet": st.column_config.NumberColumn(step=0.1),
            "Kur (TL)": st.column_config.NumberColumn(
                format="%.4f",
                step=0.0001,
                help="Otomatik varsa üstüne yazar; otomatik yoksa manuel gir."
            ),
            "Tutar (TL)": st.column_config.NumberColumn(
                format="%.2f",
                step=1.0,
                help="Otomatik: Kur * Adet"
            ),
            "Kod": st.column_config.TextColumn(help="TRY, USD, EUR, GRAM, CEYREK, YARIM, ATA, BILEZIK"),
        },
        disabled=["Tutar (TL)"],
        key="assets_editor",
    )

keep_cols_assets = ["Varlık Türü", "Kod", "Adet", "Kur (TL)", "Not"]
for c in keep_cols_assets:
    if c not in edited_assets.columns:
        edited_assets[c] = None
st.session_state["assets_df"] = edited_assets[keep_cols_assets].copy()

st.divider()

# ----------------------------
# Debts table
# ----------------------------

st.subheader("Borçlar")
debts_col, _empty2 = st.columns([1, 1])  # %50 tablo, %50 boş
with debts_col:
    debts_df = st.data_editor(
        st.session_state["debts_df"],
        use_container_width=True,
        num_rows="dynamic",
        column_config={"Tutar (TL)": st.column_config.NumberColumn(step=10.0)},
        key="debts_editor",
    )
st.session_state["debts_df"] = debts_df

# Totals
display_df2 = compute_display_assets(st.session_state["assets_df"], snap.prices_try, use_side=use_side)
total_assets, total_debts, net_total = compute_totals(display_df2, debts_df)

# ----------------------------
# AUTO NET SNAPSHOT (BUGÜN)
# ----------------------------
ensure_baseline_net(st.session_state)  # 2026-01-28 = 2.000.000 garanti

today_str = dt.date.today().isoformat()
upsert_net_snapshot(st.session_state, today_str, net_total)

st.divider()

# ----------------------------
# Summary
# ----------------------------

st.subheader("Toplam Bilanço")
st.metric("Toplam Varlık (TL)", f"{total_assets:,.2f}")
st.metric("Toplam Borç (TL)", f"{total_debts:,.2f}")
st.metric("Net (TL)", f"{net_total:,.2f}")

# Auto snapshot at >= 23:59 (requires page rerun around that time)
now = dt.datetime.now()
today_str = now.date().isoformat()
if (now.hour > 23) or (now.hour == 23 and now.minute >= 59):
    upsert_net_snapshot(st.session_state, today_str, net_total)

# ----------------------------
# Cash Flow (baseline-relative)
# ----------------------------

st.divider()
st.subheader("Kar/Zarar Durumu")
st.caption("Kâr/Zarar = Seçili Gün Net(TL) − Referans Gün Net(TL). (23:59 snapshot)")

cf_col, _empty3 = st.columns([1, 1])
with cf_col:
    today = dt.date.today()
    start_day = today - dt.timedelta(days=30)

    selected_date = st.date_input(
        "Tarih seç (son 30 gün)",
        value=today,
        min_value=start_day,
        max_value=today,
        key="cashflow_date"
    )

    base_default = dt.date.fromisoformat(st.session_state["cashflow_base_date"])
    base_date = st.date_input(
        "Referans Gün (Baseline)",
        value=base_default,
        min_value=dt.date(2000, 1, 1),
        max_value=today,
        key="cashflow_base_picker"
    )
    st.session_state["cashflow_base_date"] = base_date.isoformat()

    sel_str = selected_date.isoformat()
    base_str = base_date.isoformat()

    sel_net = get_net_for(st.session_state, sel_str)
    base_net = get_net_for(st.session_state, base_str)

    if base_net is None:
        st.error(f"Referans gün ({base_str}) için net kaydı yok. (O gün snapshot alınmamış.)")
    elif sel_net is None:
        st.warning(f"{sel_str} için net kaydı yok. (O gün snapshot alınmamış.)")
        st.write(f"**Referans Net ({base_str} 23:59):** {base_net:,.2f} TL")
    else:
        pnl = sel_net - base_net
        st.metric("Seçili Gün Net (TL)", f"{sel_net:,.2f}", delta=f"{pnl:+,.2f} (referansa göre)")
        st.write(f"**Referans Net ({base_str} 23:59):** {base_net:,.2f} TL")

    nh = st.session_state.get("net_history", [])
    if nh and base_net is not None:
        df_nh = pd.DataFrame(nh).copy()
        df_nh = df_nh.sort_values("date")
        df_nh = df_nh[df_nh["date"] >= start_day.isoformat()]

        df_nh["Referansa Göre Kâr/Zarar (TL)"] = df_nh["net"].astype(float) - float(base_net)
        df_show = df_nh.rename(columns={"date": "Gün", "net": "23:59 Net (TL)"})[
            ["Gün", "23:59 Net (TL)", "Referansa Göre Kâr/Zarar (TL)"]
        ]
        st.dataframe(df_show, use_container_width=True, height=260)
    else:
        st.info("Net snapshot listesi boş veya referans net bulunamadı. En az bir gün için snapshot gerekli.")

# ----------------------------
# Prices info
# ----------------------------

st.divider()
st.subheader("Fiyat Kaynağı")
st.write(f"**Update_Date:** {snap.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}")
st.write(f"**Kaynak:** {snap.source}")
if snap.notes:
    st.info(snap.notes)

st.subheader("Mevcut Fiyatlar (TRY) — Buying")

prices_col, _empty = st.columns([1, 1])  # %50 tablo, %50 boş

with prices_col:
    if snap.prices_try:
        dfp = pd.DataFrame(
            [{"Kod": k, "TRY": v} for k, v in sorted(snap.prices_try.items())]
        )
        st.dataframe(dfp, use_container_width=True, height=300)
    else:
        st.warning(
            "Fiyatlar boş. İnternet veya site engeli olabilir. "
            "'Kur (TL)' alanına manuel yazabilirsin."
        )

# ----------------------------
# Download (Excel) + Save now
# ----------------------------

xlsx_bytes = build_bilanco_xlsx(display_df2, debts_df)

st.sidebar.download_button(
    "Bilançoyu İndir (Excel)",
    data=xlsx_bytes,
    file_name="bilanco.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

if st.session_state.get("force_save_state"):
    payload = {
        "assets": st.session_state["assets_df"].to_dict(orient="records"),
        "debts": st.session_state["debts_df"].to_dict(orient="records"),
        "saved_at": dt.datetime.now().isoformat(timespec="seconds"),
        "net_history": st.session_state.get("net_history", []),
        "cashflow_base_date": st.session_state.get("cashflow_base_date", "2026-01-28"),
    }
    save_state(state_path, payload)
    st.sidebar.success("Kaydedildi.")
    st.session_state["force_save_state"] = False


def sum_two_integers(a: int, b: int) -> int:
    return a + b
