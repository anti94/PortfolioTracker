import pandas as pd


DEFAULT_ASSETS = pd.DataFrame(
    [
        {"Varlık Türü": "Banka (TL)", "Kod": "TRY", "Adet": 400000.0, "Kur (TL)": 1.0, "Not": ""},
        {"Varlık Türü": "Euro", "Kod": "EUR", "Adet": 600.0, "Kur (TL)": None, "Not": ""},
        {"Varlık Türü": "Ata Altın", "Kod": "ATA", "Adet": 24.0, "Kur (TL)": None, "Not": ""},
        {"Varlık Türü": "22-ayar-bilezik", "Kod": "BILEZIK", "Adet": 5 * 10, "Kur (TL)": None, "Not": "bilezik otomatik yoksa manuel gir"},
        {"Varlık Türü": "Çeyrek", "Kod": "CEYREK", "Adet": 1.0, "Kur (TL)": None, "Not": ""},
        {"Varlık Türü": "Gram Altın", "Kod": "GRAM", "Adet": 4.5, "Kur (TL)": None, "Not": ""},
        {"Varlık Türü": "Çeyrek", "Kod": "CEYREK", "Adet": 7.0, "Kur (TL)": None, "Not": ""},
        {"Varlık Türü": "Yarım", "Kod": "YARIM", "Adet": 1.0, "Kur (TL)": None, "Not": ""},
        {"Varlık Türü": "Dolar", "Kod": "USD", "Adet": 0.0, "Kur (TL)": None, "Not": ""},
    ]
)

DEFAULT_DEBTS = pd.DataFrame(
    [{"Borç Adı": "Kredi Kartı", "Tutar (TL)": 130000.0, "Not": ""}]
)
