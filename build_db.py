#!/usr/bin/env python3
"""Build a SQLite database from the Berka (PKDD'99) financial dataset files.

Put the Berka data files in the ./data directory first, then run:

    python build_db.py

Every *.csv / *.asc / *.tsv / *.txt file in ./data is loaded into a table named
after the file (loan.csv -> table "loan"). Delimiters are auto-detected, so the
original semicolon-separated .asc files and comma-separated Kaggle CSVs both work.
The result is written to ./berka.db, which is what the app reads.
"""
from __future__ import annotations

import sys
from pathlib import Path
import sqlite3

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = Path(__file__).parent / "berka.db"

# The transactions table has ~1M rows. Capping keeps the committed .db small
# enough for free hosting. Set to None to load every row.
MAX_ROWS_PER_TABLE: int | None = 100_000

DATA_EXTENSIONS = {".csv", ".asc", ".tsv", ".txt"}


def find_data_files() -> list[Path]:
    if not DATA_DIR.exists():
        sys.exit(f"Data directory not found: {DATA_DIR}\n"
                 "Create it and add the Berka data files (see README).")
    files = [p for p in sorted(DATA_DIR.iterdir())
             if p.suffix.lower() in DATA_EXTENSIONS]
    if not files:
        sys.exit(f"No data files found in {DATA_DIR}.\n"
                 "Download the Berka dataset and drop the files there (see README).")
    return files


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert columns that are entirely numeric into real numbers so SQL
    aggregates (SUM, AVG, comparisons) behave correctly."""
    for col in df.columns:
        non_empty = df[col].astype(str).str.strip() != ""
        if non_empty.sum() == 0:
            continue
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted[non_empty].notna().mean() >= 0.99:
            df[col] = converted
    return df


def load_file(path: Path) -> pd.DataFrame:
    # sep=None + engine="python" auto-detects ',', ';' or tab delimiters.
    df = pd.read_csv(path, sep=None, engine="python", dtype=str,
                     keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if MAX_ROWS_PER_TABLE is not None and len(df) > MAX_ROWS_PER_TABLE:
        df = df.head(MAX_ROWS_PER_TABLE)
    return coerce_types(df)


def main() -> None:
    files = find_data_files()
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        for path in files:
            table = path.stem.strip().lower()
            df = load_file(path)
            df.to_sql(table, conn, if_exists="replace", index=False)
            print(f"  loaded {len(df):>7} rows -> table '{table}'  ({path.name})")
        conn.commit()
    finally:
        conn.close()
    size_mb = DB_PATH.stat().st_size / 1_000_000
    print(f"\nDone. Wrote {DB_PATH} ({size_mb:.1f} MB).")


if __name__ == "__main__":
    main()
