STATE_FILE = "portfolio_state.json"
DEFAULT_STATE_FILE = "portfolio_state.json"

ASSET_COLS = ["Varlık Türü", "Kod", "Adet", "Kur (TL)", "Not"]
DEBT_COLS = ["Borç Adı", "Tutar (TL)", "Not"]

AUTO_PRICE_KEY = {
    "USD": ("USDTRY_BUY", "USDTRY_SELL"),
    "EUR": ("EURTRY_BUY", "EURTRY_SELL"),
    "GRAM": ("GRAM_BUY", "GRAM_SELL"),
    "CEYREK": ("CEYREK_BUY", "CEYREK_SELL"),
    "YARIM": ("YARIM_BUY", "YARIM_SELL"),
    "ATA": ("ATA_BUY", "ATA_SELL"),
    "BILEZIK": ("BILEZIK_BUY", "BILEZIK_SELL"),
}

APP_TITLE = "Portfolio Tracker"

BASELINE_DATE = "2026-01-28"
BASELINE_NET = 2_000_000.0
