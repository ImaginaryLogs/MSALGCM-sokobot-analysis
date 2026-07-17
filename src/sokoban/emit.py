"""CSV row writer for the shared D6 schema. Appends; writes header on new file."""
from __future__ import annotations

import csv
from pathlib import Path

from .metrics import CSV_COLUMNS


def write_row(csv_path: str | Path, row: dict) -> None:
    path = Path(csv_path)
    is_new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
