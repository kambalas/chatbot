from __future__ import annotations

from pathlib import Path

import pandas as pd


def extract_text(path: Path) -> str:
    dataframe = pd.read_csv(path)
    return dataframe.to_csv(index=False)
