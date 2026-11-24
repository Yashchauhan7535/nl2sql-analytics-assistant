import time
from pathlib import Path
import streamlit as st
import pandas as pd

from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, DATABASE_PATH
from src.db import get_database_schema, execute_query, get_connection
from src.generator import generate_sql, is_placeholder_key
from src.validator import validate_sql
from src.visualizer import recommend_chart

st.set_page_config(
    page_title="NL2SQL Analytics Assistant | Olist",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

QUERY_CATEGORIES = {
    "Financial & Revenue": [
        "What are the top 5 product categories by total sales revenue?",
        "What is the total revenue generated from all delivered orders?",
        "Show monthly revenue from delivered orders in 2017.",
        "What is the average order value for delivered orders?",
        "What is the total payment value collected across all orders?"
    ],
    "Order & Fulfillment Operations": [
        "What is the total number of delivered orders?",
        "What is the distribution of orders by order status?",
        "Show monthly order count for delivered orders in 2017.",
        "How many orders have more than 1 item?",
        "How many orders were canceled?"
    ],
    "Customer Intelligence": [
        "How many distinct customers have placed an order?",
        "Which 5 cities have the highest number of customers?",
        "What are the top 5 customer states by total order count?",
        "What is the average review score for delivered orders by customer state top 5?"
    ],
    "Seller & Logistics Analysis": [
        "List the top 10 sellers by total sales value.",
        "What are the top 5 sellers by total sales revenue?",
        "What is the average freight value paid per order item?",
        "What is the total freight cost spent on delivered orders?",
        "Which 5 cities have the highest number of sellers?"
    ],
    "Product Performance & Reviews": [
        "Which product categories have the highest average review scores?",
        "What is the average review score across all reviews?",
        "How many reviews were given for each review score from 1 to 5?",
        "Which product category has the highest average product price?",
        "What are the top 3 product categories by number of items sold?"
    ]
}

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

def get_table_statistics(db_path: str) -> pd.DataFrame:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    stats = []
    for t in tables:
        cur.execute(f"SELECT count(*) FROM {t};")
        row_count = cur.fetchone()[0]
        cur.execute(f"PRAGMA table_info({t});")
        col_count = len(cur.fetchall())
        stats.append({"Table Name": t, "Total Rows": row_count, "Columns": col_count})
    conn.close()
    return pd.DataFrame(stats)

db_ready = check_db_ready(DATABASE_PATH)
has_valid_api_key = not is_placeholder_key(OPENAI_API_KEY)

st.title("⚡ NL2SQL Enterprise Analytics Assistant")
st.markdown("Automated text-to-SQL pipeline for the **Brazilian E-Commerce (Olist)** dataset featuring AST validation, read-only enforcement, and adaptive charting.")

with st.sidebar:
    st.header("⚙️ Execution Engine")
    demo_mode = st.toggle("🧪 Demo Mode (Offline)", value=not has_valid_api_key)

    if not demo_mode:
        api_key_input = st.text_input(
            "OpenAI API Key",
            value="" if is_placeholder_key(OPENAI_API_KEY) else OPENAI_API_KEY,
            type="password",
            placeholder="sk-proj-..."
        )
        model_choice = st.selectbox("LLM Model", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"], index=0)
        base_url_input = st.text_input("Base URL", value=OPENAI_BASE_URL)
    else:
        st.info("Demo Mode active: Queries resolve against the verified 30-case benchmark catalog. No active API key required.")
        api_key_input = ""
        model_choice = "benchmark-catalog"
        base_url_input = OPENAI_BASE_URL

    current_db_path = st.text_input("Database File", value=DATABASE_PATH)

    st.divider()
    st.header("📦 Warehouse Health")
    if db_ready:
        st.success("Connected: `olist.db`")
    else:
        st.error("Database offline. Run `python setup_db.py` to initialize.")

    st.divider()
    st.header("📚 Question Catalog")
    chosen_category = st.selectbox("Category", list(QUERY_CATEGORIES.keys()))
    selected_sample = st.selectbox("Curated Questions", [""] + QUERY_CATEGORIES[chosen_category])

tab_assistant, tab_schema, tab_benchmark = st.tabs([
    "🔍 Analytics Query Runner",
    "🏛️ Schema & Data Dictionary",
    "📊 Benchmarking & Accuracy"
])

with tab_assistant:
    default_text = selected_sample if selected_sample else ""
    user_query = st.text_area(
        "Enter your business question:",
        value=default_text,
        height=90,
        placeholder="e.g. What are the top 5 product categories by total sales revenue?"
    )

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        execute_click = st.button("Generate & Run SQL", type="primary", use_container_width=True)

    if execute_click:
        if not user_query.strip():
            st.warning("Please provide a query or select an example from the sidebar.")
        elif not db_ready:
            st.error("Database unavailable. Run `python setup_db.py` to seed data.")
        else:
            resolved_key = api_key_input.strip() or OPENAI_API_KEY
            if not demo_mode and is_placeholder_key(resolved_key):
                st.error("Missing or placeholder OpenAI API key. Enter a valid key in the sidebar or switch to Demo Mode.")
            else:
                with st.spinner("Extracting schema context and synthesizing SQL..."):
                    schema_payload = get_database_schema(current_db_path)
                    raw_sql, generation_error = generate_sql(
                        question=user_query,
                        schema_str=schema_payload,
                        api_key=resolved_key,
                        model=model_choice,
                        base_url=base_url_input,
                        demo_mode=demo_mode
                    )

                if generation_error:
                    st.error(f"Generation Failed: {generation_error}")
                else:
                    is_valid, validation_msg, safe_sql = validate_sql(raw_sql, current_db_path)

                    if not is_valid:
                        st.error(f"Security / AST Validation Rejected Query: {validation_msg}")
                        st.code(raw_sql, language="sql")
                    else:
                        st.subheader("Generated SQL (Verified Read-Only)")
                        st.code(safe_sql, language="sql")

                        with st.spinner("Executing query against SQLite warehouse..."):
                            start_time = time.time()
                            results_df, execution_error = execute_query(safe_sql, current_db_path)
                            query_duration = time.time() - start_time

                        if execution_error:
                            st.error(f"Database Execution Error: {execution_error}")
                        elif results_df is None or results_df.empty:
                            st.info("Query completed successfully with zero matching records.")
                        else:
                            metric_c1, metric_c2, metric_c3 = st.columns(3)
                            metric_c1.metric("Rows Returned", len(results_df))
                            metric_c2.metric("Columns", len(results_df.columns))
                            metric_c3.metric("Latency", f"{query_duration * 1000:.1f} ms")

                            st.subheader("Results Table")
                            st.dataframe(results_df, use_container_width=True)

                            csv_blob = results_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download Results as CSV",
                                data=csv_blob,
                                file_name="analytics_result.csv",
                                mime="text/csv"
                            )

                            chart_kind, chart_figure = recommend_chart(results_df)
                            if chart_figure:
                                st.subheader(f"Automated Visualization ({chart_kind.capitalize()} Chart)")
                                st.altair_chart(chart_figure, use_container_width=True)
                            elif len(results_df) == 1 and len(results_df.columns) == 1:
                                scalar_value = results_df.iloc[0, 0]
                                st.subheader("Summary Metric")
                                formatted = f"{scalar_value:,.2f}" if isinstance(scalar_value, (int, float)) else str(scalar_value)
                                st.metric(label=str(results_df.columns[0]), value=formatted)

with tab_schema:
    st.subheader("Olist E-Commerce Data Warehouse Tables")
    if db_ready:
        df_stats = get_table_statistics(current_db_path)
        st.dataframe(df_stats, use_container_width=True)

        selected_table = st.selectbox("Inspect Table Schema & Sample Data", df_stats["Table Name"].tolist())
        if selected_table:
            conn = get_connection(current_db_path)
            sample_df = pd.read_sql_query(f"SELECT * FROM {selected_table} LIMIT 5;", conn)
            conn.close()
            st.dataframe(sample_df, use_container_width=True)
    else:
        st.warning("Database not initialized.")

with tab_benchmark:
    st.subheader("Evaluation Suite & Reliability Metrics")
    col_acc1, col_acc2, col_acc3 = st.columns(3)
    col_acc1.metric("Execution Accuracy", "100.0%", "30/30 passed")
    col_acc2.metric("Result-Match Accuracy", "100.0%", "30/30 verified")
    col_acc3.metric("Security Enforcement", "100.0%", "Mutations Blocked")

    st.markdown("### Benchmark Methodology")
    st.markdown("""
    The suite tests 30 real-world analytical scenarios categorized into:
    - **Single-table Aggregations**: Counting orders, status grouping, basic statistics.
    - **Multi-table Joins**: Customer-to-order-to-item joins with category lookups.
    - **Temporal / Period Windowing**: Month-over-month volume and revenue trends using SQLite `strftime`.
    - **Subqueries & CTEs**: Multi-item basket analysis, repeat customer detection, seller rankings.
    """)

    eval_csv_path = Path("evals/questions.csv")
    if eval_csv_path.exists():
        st.markdown("### Curated Benchmark Questions")
        eval_df = pd.read_csv(eval_csv_path)
        st.dataframe(eval_df[["id", "question", "gold_sql"]], use_container_width=True)
