"""Ask the Bank — type English, get SQL, run it against the Berka dataset.

Results are shown as a table, and (when they contain numbers) as an optional
bar / line / area chart you can configure.
"""
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


def render_chart(df: pd.DataFrame) -> None:
    """Show an optional chart when the result has something worth plotting."""
    numeric = df.select_dtypes("number").columns.tolist()
    if len(df) < 2 or not numeric:
        return  # a single row or no numbers — nothing useful to chart

    non_numeric = [c for c in df.columns if c not in numeric]
    st.markdown("#### Chart")
    col_type, col_x, col_y = st.columns(3)

    with col_type:
        chart_type = st.selectbox("Chart type", ["Bar", "Line", "Area"],
                                  key="chart_type")
    with col_x:
        x_options = df.columns.tolist()
        default_x = non_numeric[0] if non_numeric else x_options[0]
        x_col = st.selectbox("X axis (labels)", x_options,
                             index=x_options.index(default_x), key="chart_x")
    with col_y:
        y_candidates = [c for c in numeric if c != x_col] or numeric
        y_cols = st.multiselect("Y axis (values)", y_candidates,
                                default=y_candidates[:1], key="chart_y")

    if not y_cols:
        st.info("Pick at least one value column to chart.")
        return

    chart_df = df[[x_col] + y_cols].copy()
    chart_df[x_col] = chart_df[x_col].astype(str)  # treat labels as categories

    if chart_type == "Bar":
        st.bar_chart(chart_df, x=x_col, y=y_cols)
    elif chart_type == "Line":
        st.line_chart(chart_df, x=x_col, y=y_cols)
    else:
        st.area_chart(chart_df, x=x_col, y=y_cols)


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
        "Show the 10 districts with the highest total loan amount.",
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

clicked = st.button("Generate SQL & run", type="primary")

if clicked and question.strip():
    # Clear any previous result so stale output doesn't linger.
    for key in ("result_sql", "result_df", "result_msg"):
        st.session_state.pop(key, None)
    try:
        with st.spinner("Asking the model…"):
            sql = ask_model(question)
        safe, reason = sql_guard.is_safe(sql)
        if not safe:
            st.session_state["result_sql"] = sql
            st.session_state["result_msg"] = ("error",
                                              f"Refused to run this query: {reason}")
        else:
            sql = sql_guard.add_limit(sql)
            try:
                df = run_query(sql)
            except Exception as exec_err:
                # One self-correction attempt: feed the error back to the model.
                with st.spinner("Query failed — asking the model to fix it…"):
                    sql = sql_guard.add_limit(ask_model(question, str(exec_err)))
                ok, why = sql_guard.is_safe(sql)
                if not ok:
                    raise RuntimeError(why)
                df = run_query(sql)
            st.session_state["result_sql"] = sql
            st.session_state["result_df"] = df
    except llm.LLMError as e:
        st.session_state["result_msg"] = ("error", f"Model error: {e}")
    except Exception as e:
        st.session_state["result_msg"] = ("error", f"Could not run the query: {e}")
elif clicked:
    st.warning("Please type a question first.")

# --- Render results (kept in session state so charts survive reruns) ---
if "result_sql" in st.session_state:
    st.code(st.session_state["result_sql"], language="sql")

if "result_msg" in st.session_state:
    level, text = st.session_state["result_msg"]
    getattr(st, level)(text)

if "result_df" in st.session_state:
    df = st.session_state["result_df"]
    st.success(f"{len(df)} row(s)")
    st.dataframe(df, use_container_width=True)
    render_chart(df)
