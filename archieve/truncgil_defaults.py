import pandas as pd

APP_TITLE = "VarlÄ±k & BorÃ§ Takip â€” Dinamik Kur/AltÄ±n"
DEFAULT_STATE_FILE = "bilanco_caglayan_hesap.json"

DEFAULT_ASSETS = pd.DataFrame(
    [
        {"VarlÄ±k TÃ¼rÃ¼": "Banka (TL)", "Kod": "TRY", "Adet": 400000.0, "Kur (TL)": 1.0, "Not": ""},
        {"VarlÄ±k TÃ¼rÃ¼": "Euro", "Kod": "EUR", "Adet": 600.0, "Kur (TL)": None, "Not": ""},
        {"VarlÄ±k TÃ¼rÃ¼": "Ata AltÄ±n", "Kod": "ATA", "Adet": 24.0, "Kur (TL)": None, "Not": ""},
        {
            "VarlÄ±k TÃ¼rÃ¼": "22-ayar-bilezik",
            "Kod": "BILEZIK",
            "Adet": 5 * 10,
            "Kur (TL)": None,
            "Not": "22-ayar-bilezik otomatik yok, kur (TL) manuel giriniz",
        },
        {"VarlÄ±k TÃ¼rÃ¼": "Ã‡eyrek", "Kod": "CEYREK", "Adet": 1.0, "Kur (TL)": None, "Not": ""},
        {
            "VarlÄ±k TÃ¼rÃ¼": "Gram AltÄ±n",
            "Kod": "GRAM",
            "Adet": 4.5,
            "Kur (TL)": None,
            "Not": "Gram altÄ±n kur degeri otomatik bulunamadi, kur (TL) manuel giriniz",
        },
        {"VarlÄ±k TÃ¼rÃ¼": "Ã‡eyrek", "Kod": "CEYREK", "Adet": 7.0, "Kur (TL)": None, "Not": ""},
        {"VarlÄ±k TÃ¼rÃ¼": "YarÄ±m", "Kod": "YARIM", "Adet": 1.0, "Kur (TL)": None, "Not": ""},
        {"VarlÄ±k TÃ¼rÃ¼": "Dolar", "Kod": "USD", "Adet": 0.0, "Kur (TL)": None, "Not": ""},
    ]
)

DEFAULT_DEBTS = pd.DataFrame(
    [
        {"BorÃ§ AdÄ±": "Kredi KartÄ±", "Tutar (TL)": 130000.0, "Not": ""},
    ]
)

AUTO_PRICE_KEY = {
    "USD": ("USDTRY_BUY", "USDTRY_SELL"),
    "EUR": ("EURTRY_BUY", "EURTRY_SELL"),
    "GRAM": ("GRAM_BUY", "GRAM_SELL"),
    "CEYREK": ("CEYREK_BUY", "CEYREK_SELL"),
    "YARIM": ("YARIM_BUY", "YARIM_SELL"),
    "ATA": ("ATA_BUY", "ATA_SELL"),
    "BILEZIK": ("BILEZIK_BUY", "BILEZIK_SELL"),
}
