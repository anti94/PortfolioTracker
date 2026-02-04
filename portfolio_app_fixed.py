from __future__ import annotations

import time
import datetime as dt
import os
import re

import pandas as pd
import streamlit as st

from app_compute import compute_display_assets, compute_totals
from app_constants import APP_TITLE, ASSET_COLS, DEBT_COLS, BASELINE_DATE, BASELINE_NET
from app_auth import (
    create_user,
    delete_user,
    get_user_role,
    is_valid_username,
    load_users,
    save_users,
    update_password,
    verify_user,
)
from app_excel import build_bilanco_xlsx
from app_net_history import ensure_baseline_net, get_net_for, upsert_net_snapshot
from app_pricing import PriceSnapshot, fetch_prices
from app_storage import load_state_from_json, save_state, save_state_to_json


# ----------------------------
# Helpers
# ----------------------------


def _parse_rate_percent(value: str) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", ".")
    if not text:
        return 0.0
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if not match:
        return 0.0
    try:
        return float(match.group(0))
    except Exception:
        return 0.0


def _normalize_asset_codes(assets_df: pd.DataFrame) -> pd.DataFrame:
    type_to_code = {
        "mevduat hesabı": "TRY",
        "banka (tl)": "TRY",
        "tl": "TRY",
        "euro": "EUR",
        "dolar": "USD",
        "usd": "USD",
        "eur": "EUR",
        "gram altın": "GRAM",
        "gram altin": "GRAM",
        "çeyrek": "CEYREK",
        "ceyrek": "CEYREK",
        "yarım": "YARIM",
        "yarim": "YARIM",
        "ata altın": "ATA",
        "ata altin": "ATA",
        "22-ayar-bilezik": "BILEZIK",
        "bilezik": "BILEZIK",
    }
    df = assets_df.copy()
    for idx, row in df.iterrows():
        asset_type = str(row.get("Varlık Türü", "")).strip().lower()
        if asset_type == "banka (tl)":
            df.at[idx, "Varlık Türü"] = "Mevduat Hesabı"
            asset_type = "mevduat hesabı"
        code = type_to_code.get(asset_type)
        if code:
            df.at[idx, "Kod"] = code
    return df


def _asset_group_from_code(code: str) -> str:
    code = str(code or "").strip().upper()
    if code in {"TRY"}:
        return "TL HESABI"
    if code in {"USD", "EUR"}:
        return "DÖVİZ HESABI"
    if code in {"GRAM", "CEYREK", "YARIM", "ATA", "BILEZIK"}:
        return "ALTIN HESABI"
    return "TL HESABI"




def apply_daily_deposit_interest(assets_df: pd.DataFrame) -> pd.DataFrame:
    now = dt.datetime.now()
    effective_date = now.date()
    if now.hour < 6:
        effective_date = effective_date - dt.timedelta(days=1)

    last_date_str = st.session_state.get("interest_last_date")
    if not last_date_str:
        st.session_state["interest_last_date"] = effective_date.isoformat()
        return assets_df

    try:
        last_date = dt.date.fromisoformat(last_date_str)
    except Exception:
        last_date = effective_date

    if effective_date <= last_date:
        return assets_df

    days = (effective_date - last_date).days
    if days <= 0:
        return assets_df

    df = assets_df.copy()
    for idx, row in df.iterrows():
        if str(row.get("Varlık Türü", "")).strip().lower() != "mevduat hesabı":
            continue
        annual_rate = _parse_rate_percent(row.get("Yıllık Faiz (%)", ""))
        if annual_rate <= 0:
            continue
        net_daily_rate = (annual_rate / 100.0) / 365.0 * (1.0 - 0.175)
        try:
            principal = float(row.get("Adet", 0.0) or 0.0)
        except Exception:
            principal = 0.0
        if principal <= 0:
            continue
        df.at[idx, "Adet"] = principal * ((1.0 + net_daily_rate) ** days)

    st.session_state["interest_last_date"] = effective_date.isoformat()
    return df


def _load_remembered_credentials() -> tuple[str, str]:
    username = str(st.session_state.get("remembered_username", "")).strip()
    password = str(st.session_state.get("remembered_password", "")).strip()
    return username, password


def _save_remembered_credentials(username: str, password: str) -> None:
    if not username:
        st.session_state["remembered_username"] = ""
        st.session_state["remembered_password"] = ""
        return
    st.session_state["remembered_username"] = username
    st.session_state["remembered_password"] = password


def _inject_localstorage_prefill() -> None:
    js = """
    <script>
    (function () {
      const uKey = "portfolio_remember_username";
      const pKey = "portfolio_remember_password";
      const rKey = "portfolio_remember_enabled";

      function setInputValue(selector, value) {
        const el = document.querySelector(selector);
        if (!el || el.value) return;
        el.value = value || "";
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }

      function setCheckbox(selector, checked) {
        const el = document.querySelector(selector);
        if (!el) return;
        if (el.checked === checked) return;
        el.checked = checked;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }

      const username = localStorage.getItem(uKey) || "";
      const password = localStorage.getItem(pKey) || "";
      const remember = (localStorage.getItem(rKey) || "") === "1";

      setTimeout(() => {
        setInputValue('input[aria-label="Kullanıcı adı"]', username);
        setInputValue('input[aria-label="Şifre"]', password);
        setCheckbox('input[aria-label="Beni hatırla"]', remember && !!username);
      }, 50);
    })();
    </script>
    """
    st.components.v1.html(js, height=0)


def _persist_remember_in_browser(username: str, password: str) -> None:
    js = f"""
    <script>
    (function () {{
      localStorage.setItem("portfolio_remember_username", {username!r});
      localStorage.setItem("portfolio_remember_password", {password!r});
      localStorage.setItem("portfolio_remember_enabled", "1");
    }})();
    </script>
    """
    st.components.v1.html(js, height=0)


def _clear_remember_in_browser() -> None:
    js = """
    <script>
    (function () {
      localStorage.removeItem("portfolio_remember_username");
      localStorage.removeItem("portfolio_remember_password");
      localStorage.removeItem("portfolio_remember_enabled");
    })();
    </script>
    """
    st.components.v1.html(js, height=0)


# ----------------------------
# UI
# ----------------------------


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# ----------------------------
# Auth
# ----------------------------

st.session_state.setdefault("auth", {"logged_in": False, "username": None, "role": "user"})
users_data = load_users("users.json")

if not st.session_state["auth"]["logged_in"]:
    login_tab, signup_tab = st.tabs(["Giriş", "Kayıt Ol"])

    with login_tab:
        st.subheader("Giriş")
        with st.form("login_form"):
            remembered_username, remembered_password = _load_remembered_credentials()
            username = st.text_input("Kullanıcı adı", value=remembered_username)
            password = st.text_input("Şifre", type="password", value=remembered_password)
            remember_me = st.checkbox("Beni hatırla", value=bool(remembered_username))
            st.caption("Not: Beni hatırla bu cihazın tarayıcısında saklar. İsterseniz tarayıcı şifre yöneticisini de kullanabilirsiniz.")
            submitted = st.form_submit_button("Giriş Yap")
        _inject_localstorage_prefill()

        if submitted:
            username_clean = username.strip()
            if verify_user(users_data, username_clean, password):
                st.session_state["auth"] = {
                    "logged_in": True,
                    "username": username_clean,
                    "role": get_user_role(users_data, username_clean),
                }
                if remember_me:
                    _save_remembered_credentials(username_clean, password)
                    _persist_remember_in_browser(username_clean, password)
                else:
                    _save_remembered_credentials("", "")
                    _clear_remember_in_browser()
                st.success("Giriş başarılı.")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")

    with signup_tab:
        st.subheader("Kayıt Ol")
        with st.form("signup_form"):
            new_username = st.text_input("Kullanıcı adı (3-32 karakter)")
            new_password = st.text_input("Şifre (en az 6 karakter)", type="password")
            new_password2 = st.text_input("Şifre (tekrar)", type="password")
            submitted_signup = st.form_submit_button("Kayıt Ol")

        if submitted_signup:
            if new_password != new_password2:
                st.error("Şifreler eşleşmiyor.")
            else:
                ok, msg = create_user(users_data, new_username, new_password, role="user")
                if ok:
                    save_users(users_data, "users.json")
                    st.success("Kayıt başarılı. Şimdi giriş yapabilirsiniz.")
                else:
                    st.error(msg)

    st.stop()

username = st.session_state["auth"]["username"]
role = st.session_state["auth"]["role"]
user_dir = os.path.join("user_data", username)
os.makedirs(user_dir, exist_ok=True)
state_path = os.path.join(user_dir, "state.json")

# If user has no personal state yet, try to migrate legacy global state
legacy_state_path = "portfolio_state.json"
if not os.path.exists(state_path) and os.path.exists(legacy_state_path):
    legacy_data = load_state_from_json(legacy_state_path)
    if legacy_data:
        save_state(state_path, legacy_data)

# Sidebar controls FIRST (so reruns see flags)
st.sidebar.header("Ayarlar")
st.sidebar.text_input("Kayıt dosyası", value=state_path, disabled=True)
refresh_sec = st.sidebar.number_input("Oto yenileme (sn) — 0 kapalı", min_value=0, max_value=3600, value=60, step=10)
use_side = "BUY"
timeout_s = st.sidebar.slider("Fiyat çekme timeout (sn)", min_value=3, max_value=30, value=10)

# --- Nonce for cache busting (important)
st.session_state.setdefault("prices_nonce", 0)

st.sidebar.divider()
st.sidebar.caption(f"Kullanıcı: {username} ({role})")


if role == "admin":
    st.sidebar.subheader("Admin Panel")
    with st.sidebar.expander("Kullanıcı Ekle / Güncelle", expanded=False):
        admin_new_username = st.text_input("Kullanıcı adı", key="admin_new_username")
        admin_new_password = st.text_input("Şifre", type="password", key="admin_new_password")
        admin_role = st.selectbox("Rol", options=["user", "admin"], key="admin_new_role")
        if st.button("Kullanıcı Ekle", key="admin_add_user"):
            ok, msg = create_user(users_data, admin_new_username, admin_new_password, role=admin_role)
            if ok:
                save_users(users_data, "users.json")
                st.success(msg)
            else:
                st.error(msg)

    with st.sidebar.expander("Şifre Değiştir", expanded=False):
        target_user = st.text_input("Kullanıcı adı", key="admin_pw_user")
        new_pw = st.text_input("Yeni şifre", type="password", key="admin_pw_new")
        if st.button("Şifreyi Güncelle", key="admin_pw_update"):
            ok, msg = update_password(users_data, target_user, new_pw)
            if ok:
                save_users(users_data, "users.json")
                st.success(msg)
            else:
                st.error(msg)

    with st.sidebar.expander("Kullanıcı Sil", expanded=False):
        delete_user_name = st.text_input("Kullanıcı adı", key="admin_delete_user")
        if st.button("Kullanıcıyı Sil", key="admin_delete_user_btn"):
            if delete_user_name == username:
                st.error("Kendi hesabınızı silemezsiniz.")
            else:
                ok, msg = delete_user(users_data, delete_user_name)
                if ok:
                    save_users(users_data, "users.json")
                    st.success(msg)
                else:
                    st.error(msg)


# =========================
# Force Load / Save handlers
# =========================
if st.session_state.get("force_reload_state"):
    data = load_state_from_json(state_path)
    if data:
        assets = pd.DataFrame(data.get("assets", []))
        debts  = pd.DataFrame(data.get("debts", []))

        # kolon fix
        for c in ASSET_COLS:
            if c not in assets.columns:
                if c == "Kod":
                    assets[c] = "TRY"
                elif c in ("Varlık Türü", "Not"):
                    assets[c] = ""
                else:
                    assets[c] = 0.0
        assets = assets[ASSET_COLS]
        assets = _normalize_asset_codes(assets)

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
    save_state_to_json(state_path, st.session_state)
    st.sidebar.success("Bilanço Durumu JSON'a kaydedildi.")
    st.session_state["force_save_state"] = False


st.sidebar.divider()

# =========================
# Init session (FROM JSON)
# =========================
if "initialized" not in st.session_state:
    data = load_state_from_json(state_path)

    if data:
        assets = pd.DataFrame(data.get("assets", []))
        debts  = pd.DataFrame(data.get("debts", []))
        st.session_state["cashflow_base_date"] = data.get("cashflow_base_date", dt.date.today().isoformat())
        st.session_state["baseline_date"] = data.get("baseline_date", BASELINE_DATE)
        st.session_state["baseline_net"] = data.get("baseline_net", BASELINE_NET)
        st.session_state["interest_last_date"] = data.get("interest_last_date")
    else:
        assets = pd.DataFrame([{
            "Varlık Türü": "Mevduat Hesabı",
            "Kod": "TRY",
            "Adet": 0.0,
            "Kur (TL)": 0.0,
            "Yıllık Faiz (%)": 0.0,
            "Not": "",
        }], columns=ASSET_COLS)
        debts  = pd.DataFrame([{
            "Borç Adı": "",
            "Tutar (TL)": 0.0,
            "Not": "",
        }], columns=DEBT_COLS)
        today_iso = dt.date.today().isoformat()
        st.session_state["baseline_date"] = today_iso
        st.session_state["baseline_net"] = 0.0
        st.session_state["cashflow_base_date"] = today_iso
        st.session_state["interest_last_date"] = today_iso

    # kolonları garanti altına al
    for c in ASSET_COLS:
        if c not in assets.columns:
            if c == "Kod":
                assets[c] = "TRY"
            elif c in ("Varlık Türü", "Not"):
                assets[c] = ""
            else:
                assets[c] = 0.0
    assets = assets[ASSET_COLS]
    assets = _normalize_asset_codes(assets)

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

    # İlk girişte kullanıcı dosyasını oluştur
    if not os.path.exists(state_path):
        save_state_to_json(state_path, st.session_state)


st.session_state.setdefault("prices_snap", PriceSnapshot(prices_try={}, fetched_at=dt.datetime.now(), source="N/A"))
st.session_state.setdefault("net_history", [])
st.session_state.setdefault("cashflow_base_date", st.session_state.get("baseline_date", BASELINE_DATE))
st.session_state.setdefault("interest_last_date", dt.date.today().isoformat())


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
# Assets tables (3 groups)
# ----------------------------

st.subheader("Varlıklar")
st.caption("Tutar otomatik = Kur * Adet.")

# Günlük faiz işletimi (Mevduat hesabı)
st.session_state["assets_df"] = apply_daily_deposit_interest(st.session_state["assets_df"])
st.session_state["assets_df"] = _normalize_asset_codes(st.session_state["assets_df"])

assets_df_base = st.session_state["assets_df"].copy()
assets_df_base["__group__"] = assets_df_base["Kod"].apply(_asset_group_from_code)

groups = [
    ("TL HESABI", "TL HESABI", "info"),
    ("DÖVİZ HESABI", "DÖVİZ HESABI", "success"),
    ("ALTIN HESABI", "ALTIN HESABI", "warning"),
]

display_cols_assets_tl = ["Varlık Türü", "Adet", "Kur (TL)", "Yıllık Faiz (%)", "Tutar (TL)", "Not"]
display_cols_assets_other = ["Varlık Türü", "Adet", "Kur (TL)", "Tutar (TL)", "Not"]
keep_cols_assets = ["Varlık Türü", "Kod", "Adet", "Kur (TL)", "Yıllık Faiz (%)", "Not"]

edited_groups = []
for group_key, group_label, group_style in groups:
    if group_style == "info":
        st.info(group_label)
    elif group_style == "success":
        st.success(group_label)
    else:
        st.warning(group_label)
    group_df = assets_df_base[assets_df_base["__group__"] == group_key].copy()
    display_df = compute_display_assets(group_df, snap.prices_try, use_side=use_side)

    display_cols = display_cols_assets_tl if group_key == "TL HESABI" else display_cols_assets_other
    display_df = display_df.reindex(columns=display_cols, fill_value=None)
    edited = st.data_editor(
        display_df[display_cols],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Adet": st.column_config.NumberColumn(step=0.1),
            "Kur (TL)": st.column_config.NumberColumn(
                format="%.4f",
                step=0.0001,
                help="Otomatik varsa üstüne yazar; otomatik yoksa manuel gir."
            ),
            "Yıllık Faiz (%)": st.column_config.NumberColumn(
                format="%.2f",
                step=0.1,
                help="Mevduat hesabı için yıllık faiz oranı (ör. 41)."
            ),
            "Tutar (TL)": st.column_config.NumberColumn(
                format="%.2f",
                step=1.0,
                help="Otomatik: Kur * Adet"
            ),
        },
        disabled=["Tutar (TL)"],
        key=f"assets_editor_{group_key}",
    )

    for c in keep_cols_assets:
        if c not in edited.columns:
            edited[c] = None
    edited_groups.append(edited[keep_cols_assets].copy())

st.session_state["assets_df"] = _normalize_asset_codes(pd.concat(edited_groups, ignore_index=True))

# ----------------------------
# Debts table
# ----------------------------

st.error("BORÇLAR")
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
st.write(f"**Update_Date:** {snap.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}")
st.subheader("Mevcut Fiyatlar (TRY) — Alış/Satış")

prices_col, _empty = st.columns([1, 1])  # %50 tablo, %50 boş

with prices_col:
    if snap.prices_try:
        price_rows = []
        code_order = [
            ("USD", "Dolar (USD)"),
            ("EUR", "Euro (EUR)"),
            ("GRAM", "Gram Altın"),
            ("CEYREK", "Çeyrek Altın"),
            ("YARIM", "Yarım Altın"),
            ("ATA", "Ata Altın"),
            ("BILEZIK", "Bilezik"),
        ]
        seen = set()
        for code, label in code_order:
            buy_key = f"{code}_BUY"
            sell_key = f"{code}_SELL"
            buy_val = snap.prices_try.get(buy_key)
            sell_val = snap.prices_try.get(sell_key, buy_val)
            price_rows.append({
                "Varlık": label,
                "Alış (TL)": buy_val,
                "Satış (TL)": sell_val,
            })
            seen.add(label.lower())

        # Add all items that contain "ALTIN" from raw data
        if snap.raw_data:
            for _, item in snap.raw_data.items():
                if not isinstance(item, dict):
                    continue
                name = str(item.get("Name") or item.get("name") or "")
                if "ALTIN" not in name.upper():
                    continue
                label = name.strip()
                if not label:
                    continue
                if label.lower() in seen:
                    continue
                buying = item.get("Buying") or item.get("buying") or item.get("Alış") or item.get("alis")
                selling = item.get("Selling") or item.get("selling") or item.get("Satış") or item.get("satis")
                price_rows.append({
                    "Varlık": label,
                    "Alış (TL)": buying,
                    "Satış (TL)": selling if selling is not None else buying,
                })
                seen.add(label.lower())

        dfp = pd.DataFrame(price_rows)
        st.dataframe(dfp, use_container_width=True, height=300)
    else:
        st.warning(
            "Fiyatlar boş. İnternet veya site engeli olabilir. "
            "'Kur (TL)' alanına manuel yazabilirsin."
        )

if snap.raw_data:
    with st.expander("Ham Kur Tablosu (Tüm Kalemler)"):
        rows = []
        for code, item in snap.raw_data.items():
            if not isinstance(item, dict):
                continue
            name = item.get("Name") or item.get("name") or ""
            buying = item.get("Buying") or item.get("buying") or item.get("Alış") or item.get("alis")
            selling = item.get("Selling") or item.get("selling") or item.get("Satış") or item.get("satis")
            change = item.get("Change") or item.get("change") or item.get("Degisim") or item.get("degisim")
            rows.append({
                "Kod": code,
                "Ad": name,
                "Alış": buying,
                "Satış": selling,
                "Değişim": change,
            })
        if rows:
            df_raw = pd.DataFrame(rows)
            st.dataframe(df_raw, use_container_width=True, height=400)

# ----------------------------
# Download (Excel) + Save now
# ----------------------------

xlsx_bytes = build_bilanco_xlsx(display_df2, debts_df)

if st.session_state.get("force_save_state"):
    payload = {
        "assets": st.session_state["assets_df"].to_dict(orient="records"),
        "debts": st.session_state["debts_df"].to_dict(orient="records"),
        "saved_at": dt.datetime.now().isoformat(timespec="seconds"),
        "net_history": st.session_state.get("net_history", []),
        "cashflow_base_date": st.session_state.get("cashflow_base_date", "2026-01-28"),
        "baseline_date": st.session_state.get("baseline_date", BASELINE_DATE),
        "baseline_net": st.session_state.get("baseline_net", BASELINE_NET),
        "interest_last_date": st.session_state.get("interest_last_date"),
    }
    save_state(state_path, payload)
    st.sidebar.success("Kaydedildi.")
    st.session_state["force_save_state"] = False

# Sidebar action buttons (bottom)
if st.sidebar.button("Kurları Güncelle"):
    # Force bypass cache: bump nonce + clear cache + set flag
    st.session_state["prices_nonce"] += 1
    st.session_state["force_refresh_prices"] = True
    try:
        cached_prices.clear()
    except Exception:
        pass

if st.sidebar.button("Bilançoyu Kaydet"):
    st.session_state["force_save_state"] = True
if st.sidebar.button("Bilançoyu Yükle"):
    st.session_state["force_reload_state"] = True
st.sidebar.download_button(
    "Bilançoyu İndir (Excel)",
    data=xlsx_bytes,
    file_name="bilanco.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
if st.sidebar.button("Çıkış Yap"):
    st.session_state["auth"] = {"logged_in": False, "username": None, "role": "user"}
    st.rerun()



def sum_two_integers(a: int, b: int) -> int:
    return a + b
