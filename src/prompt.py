FEW_SHOT_EXAMPLES = """
Example 1:
Question: What are the top 5 product categories by total sales revenue?
SQL:
SELECT
    COALESCE(t.product_category_name_english, p.product_category_name) AS category,
    ROUND(SUM(oi.price), 2) AS total_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY category
ORDER BY total_revenue DESC
LIMIT 5;

Example 2:
Question: Show monthly order volume and total revenue for 2017.
SQL:
SELECT
    strftime('%Y-%m', o.order_purchase_timestamp) AS order_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(oi.price), 2) AS total_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
  AND strftime('%Y', o.order_purchase_timestamp) = '2017'
GROUP BY order_month
ORDER BY order_month ASC;

Example 3:
Question: What is the average review score for each payment type?
SQL:
SELECT
    p.payment_type,
    ROUND(AVG(r.review_score), 2) AS avg_review_score,
    COUNT(DISTINCT o.order_id) AS order_count
FROM order_payments p
JOIN orders o ON p.order_id = o.order_id
JOIN order_reviews r ON o.order_id = r.order_id
GROUP BY p.payment_type
ORDER BY avg_review_score DESC;

Example 4:
Question: Which 5 states have the highest number of customers?
SQL:
SELECT
    customer_state,
    COUNT(customer_id) AS customer_count
FROM customers
GROUP BY customer_state
ORDER BY customer_count DESC
LIMIT 5;
"""

def build_system_prompt(schema_str: str) -> str:
    return f"""You are an expert SQL analytics engineer specializing in SQLite.
Your goal is to convert plain-English business questions into accurate, high-performance SQLite SELECT queries.

Database Schema:
{schema_str}

Important Guidelines:
1. Generate valid, read-only SQLite SELECT queries. Never use mutations (INSERT, UPDATE, DELETE, DROP, etc.).
2. When calculating completed sales or revenue, filter by `orders.order_status = 'delivered'` unless explicitly asked otherwise.
3. For category names, prefer the English translation from `product_category_name_translation.product_category_name_english` joined on `product_category_name`.
4. Format dates and timestamps using SQLite functions like `strftime('%Y-%m', ...)` or `strftime('%Y', ...)`.
5. Use ROUND(..., 2) for monetary metrics and percentage/average values where appropriate.
6. Always alias calculated columns with meaningful names (e.g. `total_revenue`, `avg_order_value`, `order_count`).
7. Return ONLY the raw SQL query inside a markdown ```sql code block, without conversational filler or explanation.

Few-Shot Examples:
{FEW_SHOT_EXAMPLES}
"""

def build_user_prompt(question: str) -> str:
    return f"Question: {question.strip()}\nGenerate SQLite SQL query:"
