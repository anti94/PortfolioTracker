import io

import pandas as pd


def build_bilanco_xlsx(assets_df: pd.DataFrame, debts_df: pd.DataFrame) -> bytes:
    """Create an Excel file in-memory with 2 sheets: Varlıklar, Borçlar."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        assets_df.to_excel(writer, index=False, sheet_name="Varlıklar")
        debts_df.to_excel(writer, index=False, sheet_name="Borçlar")
    return output.getvalue()
