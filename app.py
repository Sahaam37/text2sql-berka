"""Ask the Bank — type English, get SQL, run it against the Berka dataset."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import llm
import sql_guard
from schema import get_connection, get_schema_prompt

st.set_page_config(page_title="Ask the Bank — English to SQL",
                   page_icon="🏦", layout="wide")

SYSTEM_PROMPT = (
    "You translate English questions into a single SQLite SELECT query.\n"
    "Rules:\n"
    "- Output ONLY the SQL. No explanation, no markdown code fences.\n"
    "- Read-only: never write INSERT / UPDATE / DELETE / DDL.\n"
    "- Use only the tables and columns in the schema below.\n"
    "- 'order' is a reserved word; always write it quoted as \"order\".\n"
    "- Add a sensible LIMIT when a question could return many rows.\n\n"
    "Schema:\n" + get_schema_prompt()
)


@st.cache_data(show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection(read_only=True)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def ask_model(question: str, error: str | None = None) -> str:
    user = question
    if error:
        user = (f"{question}\n\nThe previous query failed with this error:\n"
                f"{error}\nReturn a corrected SQLite query.")
    return sql_guard.clean_sql(llm.generate_sql(SYSTEM_PROMPT, user))


st.title("🏦 Ask the Bank")
st.caption("Type a question in plain English. It gets turned into SQL and run "
           "against the Berka Czech-bank dataset.")

with st.sidebar:
    st.subheader("Model")
    st.write(llm.provider_label())
    st.subheader("Try asking")
    for ex in [
        "How many clients are there?",
        "What is the average loan amount by loan status?",
        "Show the 10 accounts with the most transactions.",
        "Total loan amount granted in each year.",
        "How many credit cards of each type were issued?",
    ]:
        if st.button(ex, key=ex):
            st.session_state["question"] = ex
    with st.expander("View database schema"):
        st.code(get_schema_prompt(), language="sql")

question = st.text_input("Your question",
                         value=st.session_state.get("question", ""),
                         placeholder="e.g. Which district has the most clients?")

if st.button("Generate SQL & run", type="primary") and question.strip():
    try:
        with st.spinner("Asking the model…"):
            sql = ask_model(question)
        safe, reason = sql_guard.is_safe(sql)
        if not safe:
            st.error(f"Refused to run this query: {reason}")
            st.code(sql, language="sql")
        else:
            sql = sql_guard.add_limit(sql)
            st.code(sql, language="sql")
            try:
                df = run_query(sql)
            except Exception as exec_err:
                # One self-correction attempt: feed the error back to the model.
                with st.spinner("Query failed — asking the model to fix it…"):
                    sql = sql_guard.add_limit(ask_model(question, str(exec_err)))
                ok, why = sql_guard.is_safe(sql)
                if not ok:
                    raise RuntimeError(why)
                st.code(sql, language="sql")
                df = run_query(sql)
            st.success(f"{len(df)} row(s)")
            st.dataframe(df, use_container_width=True)
    except llm.LLMError as e:
        st.error(f"Model error: {e}")
    except Exception as e:
        st.error(f"Could not run the query: {e}")
