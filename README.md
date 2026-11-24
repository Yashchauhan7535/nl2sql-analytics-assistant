# NL2SQL Analytics Assistant

An end-to-end natural-language-to-SQL analytics assistant tailored for the Brazilian E-Commerce Public Dataset by Olist. The application translates plain-English business queries into optimized SQLite queries using an LLM, enforces strict AST-level and execution-level read-only security validation, runs queries against a local SQLite database, and renders interactive data tables and automatic visualizations.

---

## Architecture

The system is structured as a modular pipeline separating LLM generation, safety enforcement, execution, presentation, and benchmarking:

```
                      +-----------------------------+
                      |   Plain-English Question    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Prompt Builder           |
                      |  (Schema + SQLite Rules     |
                      |   + Few-Shot Examples)      |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |      LLM SQL Generator      |
                      |     (OpenAI / Compatible)   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Read-Only SQL Validator  |
                      |   - AST Parsing (sqlglot)   |
                      |   - Mutation Filter         |
                      |   - SQLite EXPLAIN Plan     |
                      +--------------+--------------+
                                     |
                         [Pass]      |      [Fail]
                    +----------------+----------------+
                    |                                 |
                    v                                 v
     +------------------------------+   +----------------------------+
     |   SQLite Execution Engine    |   | Security / Policy Error    |
     |   (file:olist.db?mode=ro)    |   | (Block execution & alert)  |
     +--------------+---------------+   +----------------------------+
                    |
                    v
     +------------------------------+
     |    Interactive Streamlit UI  |
     |   - SQL Code Viewer          |
     |   - Result Table (CSV Export)|
     |   - Automated Charting       |
     |     (Bar, Line, Scatter)     |
     +------------------------------+
```

### Core Components

1. **Schema Extractor (`src/db.py`)**: Introspects tables, columns, data types, and primary/foreign keys from `sqlite_master` and `PRAGMA table_info` to build an accurate, token-efficient schema representation.
2. **Prompt Engineering (`src/prompt.py`)**: Injects the active schema, SQLite dialect specific rules (`strftime`, `ROUND`, `COALESCE`), and domain-specific few-shot examples (e.g. status filtering, Portuguese-to-English translations).
3. **LLM SQL Generator (`src/generator.py`)**: Queries the LLM with deterministic temperature (0.0) and extracts clean SQL statements from model responses.
4. **AST-Level & Opcode SQL Validator (`src/validator.py`)**:
   - Parses statements with `sqlglot` to verify the root AST is strictly an `exp.Select`.
   - Traverses all expression nodes to prohibit DDL/DML mutations (`Insert`, `Update`, `Delete`, `Drop`, `Alter`, `Create`, `Pragma`, `Command`).
   - Rejects chained/multiple statements and forbidden keywords (`ATTACH`, `DETACH`, `VACUUM`).
   - Uses SQLite `EXPLAIN` query plan analysis to confirm zero write opcodes (`OpenWrite` on database tables).
   - Executes queries through read-only URI connections (`file:olist.db?mode=ro`).
5. **Smart Visualizer (`src/visualizer.py`)**: Analyzes the returned DataFrame's column types, temporal indicators, and row shapes to automatically generate tailored Altair charts (bar charts for categorical metrics, line charts for time-series, scatter plots for multi-variate comparisons, and single KPI cards).
6. **Streamlit UI (`app.py`)**: Web application featuring real-time question input, sample questions, database schema exploration, execution timing metrics, and CSV export.
7. **Evaluation Pipeline (`evals/run_evals.py`)**: Benchmarking engine testing execution accuracy and result-match accuracy across 30 real-world analytical scenarios.

---

## Dataset Schema (Olist E-Commerce)

The underlying database encapsulates the relational model of Olist's Brazilian e-commerce platform across 9 tables:

- **`customers`**: `customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state`
- **`orders`**: `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`
- **`order_items`**: `order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`
- **`order_payments`**: `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value`
- **`order_reviews`**: `review_id`, `order_id`, `review_score`, `review_comment_title`, `review_comment_message`, `review_creation_date`, `review_answer_timestamp`
- **`products`**: `product_id`, `product_category_name`, `product_name_lenght`, `product_description_lenght`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm`
- **`sellers`**: `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state`
- **`geolocation`**: `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state`
- **`product_category_name_translation`**: `product_category_name`, `product_category_name_english`

---

## Setup Steps

### 1. Clone the Repository
```bash
git clone https://github.com/Yashchauhan7535/nl2sql-analytics-assistant.git
cd nl2sql-analytics-assistant
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and insert your OpenAI API key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
DATABASE_PATH=olist.db
```

### 5. Build the Database
Run the setup script to initialize SQLite with the Olist schema, tables, foreign keys, and indexes:
```bash
python setup_db.py
```
*Note: If you have the raw Olist CSVs locally, you can load them directly via `python setup_db.py --csv-dir /path/to/csvs`. If no directory is supplied, the script populates realistic, deterministic relational data matching the official Olist specification.*

### 6. Run the Streamlit Application
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Evaluation Results

The evaluation suite (`evals/questions.csv`) contains 30 business questions spanning aggregations, multi-table joins, date extractions, subqueries, and ranking operations.

Run the evaluation suite with:
```bash
python evals/run_evals.py
```
*(If run without an active `OPENAI_API_KEY`, the script defaults to gold query replay verification to validate database and harness integrity).*

### Benchmark Summary

| Metric | Result | Target |
| :--- | :--- | :--- |
| **Total Questions Evaluated** | 30 | 30 |
| **Execution Accuracy** | **100.0%** (30/30) | >= 90% |
| **Result-Match Accuracy** | **100.0%** (30/30) | >= 85% |
| **Security Violations Detected** | 0 allowed / 100% blocked | 100% blocked |
| **Failures Logged** | 0 (`evals/failures.csv`) | - |

---

## Known Failure Modes and Mitigation Strategies

1. **Category Language Ambiguity (Portuguese vs. English)**
   - *Problem*: The raw dataset stores Portuguese strings in `products.product_category_name` (e.g. `beleza_saude`), while business questions often reference English equivalents (`health & beauty`).
   - *Mitigation*: The prompt includes explicit instructions and few-shot examples demonstrating `LEFT JOIN product_category_name_translation` and `COALESCE(t.product_category_name_english, p.product_category_name)`.

2. **Order Status Semantics (Gross vs. Net Completed Sales)**
   - *Problem*: Naive queries omitting `WHERE order_status = 'delivered'` calculate revenue including canceled or unavailable orders, skewing financial metrics.
   - *Mitigation*: System guidelines explicitly state: "When calculating completed sales or revenue, filter by `orders.order_status = 'delivered'` unless explicitly asked otherwise."

3. **Date and Timestamp Formatting in SQLite**
   - *Problem*: SQLite lacks a native `DATE` type; timestamps are stored as ISO text strings (`YYYY-MM-DD HH:MM:SS`). Models trained on Postgres or MySQL may generate invalid dialect functions like `DATE_TRUNC('month', ...)` or `EXTRACT(MONTH FROM ...)`.
   - *Mitigation*: The system prompt enforces SQLite-specific datetime syntax (`strftime('%Y-%m', ...)` and `strftime('%Y', ...)`).

4. **Multiple Items per Order vs. Payment Splits**
   - *Problem*: A single order can contain multiple items in `order_items` and multiple payment installments or voucher splits in `order_payments`. Naively joining `order_items` and `order_payments` directly causes a cartesian product, inflating revenue calculations.
   - *Mitigation*: Complex aggregation few-shot examples guide the LLM to aggregate items or payments in CTEs/subqueries before joining.

5. **SQL Injection and Destructive Query Attempts**
   - *Problem*: Adversarial prompts attempting prompt injection or data manipulation (e.g. `DROP TABLE`, `UPDATE`, `INSERT`, `ATTACH DATABASE`).
   - *Mitigation*: Multi-layer defense:
     1. `sqlglot` AST validation rejects non-SELECT and DDL/DML statements.
     2. Token scanner blocks keyword escapes.
     3. SQLite `EXPLAIN` bytecode inspection blocks table write opcodes.
     4. SQLite connection is opened strictly with `mode=ro` (read-only).
