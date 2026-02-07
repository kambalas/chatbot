from __future__ import annotations

from pathlib import Path

import pandas as pd


def extract_text(path: Path) -> str:
    sheets = pd.read_excel(path, sheet_name=None)
    parts: list[str] = []
    for sheet_name, dataframe in sheets.items():
        parts.append(f"[Sheet: {sheet_name}]")
        parts.append(dataframe.to_csv(index=False))
    return "\n".join(parts)
