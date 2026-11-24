import time
from pathlib import Path
import streamlit as st
import pandas as pd

from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, DATABASE_PATH
from src.db import get_database_schema, execute_query, get_connection
from src.generator import generate_sql
from src.validator import validate_sql
from src.visualizer import recommend_chart

st.set_page_config(
    page_title="NL2SQL Analytics Assistant",
    page_icon="📊",
    layout="wide"
)

SAMPLE_QUESTIONS = [
    "What are the top 5 product categories by total sales revenue?",
    "Show monthly order volume and total revenue for 2017.",
    "Which 5 states have the highest number of customers?",
    "What is the average review score for each payment type?",
    "List the top 10 sellers by total sales value.",
    "What percentage of orders are delivered versus canceled?",
    "What is the average freight value by customer state?",
    "Which product categories have the highest average review scores?"
]

def check_db_ready(db_path: str) -> bool:
    if not Path(db_path).exists():
        return False
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        count = cur.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False

db_ready = check_db_ready(DATABASE_PATH)

st.title("📊 NL2SQL Analytics Assistant")
st.caption("Ask natural-language business questions about the Olist e-commerce store. Powered by LLM-generated, validated read-only SQLite SQL.")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key_input = st.text_input("OpenAI API Key", value=OPENAI_API_KEY, type="password")
    model_choice = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"], index=0)
    base_url_input = st.text_input("API Base URL", value=OPENAI_BASE_URL)
    current_db_path = st.text_input("Database Path", value=DATABASE_PATH)

    st.divider()
    st.header("📁 Database Status")
    if db_ready:
        st.success("Database connected: `olist.db`")
        with st.expander("Explore Database Schema"):
            schema_text = get_database_schema(current_db_path)
            st.text(schema_text)
    else:
        st.error("Database not found! Run `python setup_db.py` to initialize.")

    st.divider()
    st.header("💡 Sample Questions")
    selected_sample = st.selectbox("Pick an example:", [""] + SAMPLE_QUESTIONS)

st.subheader("Ask a Business Question")
default_val = selected_sample if selected_sample else ""
user_question = st.text_area(
    "Enter your business question in plain English:",
    value=default_val,
    height=80,
    placeholder="e.g. What are the top 5 product categories by total sales revenue?"
)

col_run, col_clear = st.columns([1, 5])
with col_run:
    run_button = st.button("🚀 Run Analytics", type="primary", use_container_width=True)

if run_button:
    if not user_question.strip():
        st.warning("Please enter a business question.")
    elif not db_ready:
        st.error("Database is not ready. Please run `python setup_db.py` first.")
    else:
        active_api_key = api_key_input.strip() or OPENAI_API_KEY
        if not active_api_key:
            st.error("Missing OpenAI API key. Provide one in the sidebar or in your `.env` file.")
        else:
            with st.spinner("Analyzing schema and generating SQL query..."):
                t0 = time.time()
                schema_str = get_database_schema(current_db_path)
                raw_sql, gen_err = generate_sql(
                    question=user_question,
                    schema_str=schema_str,
                    api_key=active_api_key,
                    model=model_choice,
                    base_url=base_url_input
                )

            if gen_err:
                st.error(f"Generation Error: {gen_err}")
            else:
                is_valid, val_err, cleaned_sql = validate_sql(raw_sql, current_db_path)

                if not is_valid:
                    st.error(f"SQL Validation Error (Security / Policy check failed): {val_err}")
                    st.code(raw_sql, language="sql")
                else:
                    st.markdown("### Generated SQL (Validated Read-Only SELECT)")
                    st.code(cleaned_sql, language="sql")

                    with st.spinner("Executing query on SQLite..."):
                        exec_t0 = time.time()
                        df, query_err = execute_query(cleaned_sql, current_db_path)
                        exec_duration = time.time() - exec_t0

                    if query_err:
                        st.error(f"Execution Error: {query_err}")
                    elif df is None or df.empty:
                        st.info("Query executed successfully, but returned 0 rows.")
                    else:
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Rows Returned", len(df))
                        m2.metric("Columns", len(df.columns))
                        m3.metric("Execution Time", f"{exec_duration * 1000:.1f} ms")

                        st.markdown("### 📋 Results Table")
                        st.dataframe(df, use_container_width=True)

                        csv_data = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Results as CSV",
                            data=csv_data,
                            file_name="query_results.csv",
                            mime="text/csv"
                        )

                        chart_type, chart_obj = recommend_chart(df)
                        if chart_obj:
                            st.markdown(f"### 📈 Automatic Visualization ({chart_type.capitalize()} Chart)")
                            st.altair_chart(chart_obj, use_container_width=True)
                        elif len(df) == 1 and len(df.columns) == 1:
                            val = df.iloc[0, 0]
                            st.markdown("### 🎯 Key Metric")
                            st.metric(label=str(df.columns[0]), value=f"{val:,.2f}" if isinstance(val, (int, float)) else str(val))
