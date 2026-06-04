"""Read the database schema and expose a read-only connection."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "berka.db"

# Plain-English notes help the model understand Berka's cryptic columns.
SCHEMA_HINTS = """
Database: Berka — a real anonymised Czech bank (PKDD'99). Money is in Czech
koruna. Dates are integers in YYYYMMDD format (e.g. 970103 = 1997-01-03).

Tables and relationships:
- client: one row per client. client_id (PK), district_id, birth_number.
- account: one row per account. account_id (PK), district_id, frequency
  (statement frequency), date (opened).
- disp (disposition): links clients to accounts. disp_id (PK), client_id,
  account_id, type ('OWNER' or 'DISPONENT'). Join client<->account through here.
- trans (transaction): one row per transaction. trans_id (PK), account_id,
  date, type, operation, amount, balance (after the txn), k_symbol.
- "order" (permanent payment orders): order_id (PK), account_id, amount,
  k_symbol. NOTE: order is a SQL keyword — always quote it as "order".
- loan: at most one loan per account. loan_id (PK), account_id, date, amount,
  duration (months), payments (monthly payment), status
  (A=finished ok, B=finished unpaid, C=running ok, D=running in debt).
- card: credit cards. card_id (PK), disp_id, type, issued. Reach an account via
  card.disp_id -> disp.disp_id -> disp.account_id.
- district: demographic data. district_id (PK). Column names may be descriptive
  or coded a1..a16 (a2 = district name, a3 = region).

Typical joins: client -> disp -> account -> {trans, "order", loan}; card -> disp.
""".strip()


def get_connection(read_only: bool = True) -> sqlite3.Connection:
    if read_only:
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    return sqlite3.connect(DB_PATH)


def get_schema_ddl() -> str:
    """CREATE statements for every table in the database."""
    conn = get_connection(read_only=True)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND sql IS NOT NULL ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return "\n\n".join(r[0] for r in rows)


def get_schema_prompt() -> str:
    return f"{get_schema_ddl()}\n\n-- Notes --\n{SCHEMA_HINTS}"
