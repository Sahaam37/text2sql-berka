"""Swappable LLM client. Default provider is Gemini; set LLM_PROVIDER=groq to switch.

Config is read from Streamlit secrets first, then environment variables, so the
same code works locally and on Streamlit Community Cloud / Hugging Face Spaces.
"""
from __future__ import annotations

import os
import requests

try:
    import streamlit as st
    _SECRETS = dict(st.secrets) if hasattr(st, "secrets") else {}
except Exception:
    _SECRETS = {}


def _cfg(name: str, default: str = "") -> str:
    if name in _SECRETS:
        return str(_SECRETS[name])
    return os.environ.get(name, default)


PROVIDER = _cfg("LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL = _cfg("GEMINI_MODEL", "gemini-2.0-flash")
GROQ_MODEL = _cfg("GROQ_MODEL", "llama-3.3-70b-versatile")


class LLMError(RuntimeError):
    pass


def _call_gemini(system: str, user: str) -> str:
    key = _cfg("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set (see README / secrets).")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={key}")
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.0},
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code != 200:
        raise LLMError(f"Gemini API error {r.status_code}: {r.text[:300]}")
    try:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise LLMError(f"Unexpected Gemini response: {r.text[:300]}")


def _call_groq(system: str, user: str) -> str:
    key = _cfg("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY is not set (see README / secrets).")
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    r = requests.post(url, json=payload,
                      headers={"Authorization": f"Bearer {key}"}, timeout=30)
    if r.status_code != 200:
        raise LLMError(f"Groq API error {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def generate_sql(system: str, user: str) -> str:
    if PROVIDER == "groq":
        return _call_groq(system, user)
    return _call_gemini(system, user)


def provider_label() -> str:
    if PROVIDER == "groq":
        return f"Groq · {GROQ_MODEL}"
    return f"Gemini · {GEMINI_MODEL}"
