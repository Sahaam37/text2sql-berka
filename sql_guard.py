"""Validate and sanitise model-generated SQL so only read-only queries run."""
from __future__ import annotations

import re

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|"
    r"detach|reindex|vacuum|pragma|grant|revoke)\b",
    re.IGNORECASE,
)


def clean_sql(raw: str) -> str:
    """Strip markdown fences / stray labels the model may add."""
    text = raw.strip()
    text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    if text.lower().startswith("sql\n"):
        text = text[4:].strip()
    # Keep only the first statement if several are returned.
    if ";" in text:
        text = text.split(";")[0].strip() + ";"
    return text


def is_safe(sql: str) -> tuple[bool, str]:
    s = sql.strip().rstrip(";").strip()
    if not s:
        return False, "Empty query."
    lowered = s.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "Only SELECT queries are allowed."
    if FORBIDDEN.search(s):
        return False, "Query contains a forbidden (non-read-only) keyword."
    if ";" in s:  # an internal semicolon means stacked statements
        return False, "Multiple statements are not allowed."
    return True, ""


def add_limit(sql: str, limit: int = 200) -> str:
    s = sql.strip().rstrip(";")
    if re.search(r"\blimit\b", s, re.IGNORECASE):
        return s
    return f"{s} LIMIT {limit}"
