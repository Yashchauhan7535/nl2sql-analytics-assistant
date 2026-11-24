import pytest
from src.validator import validate_sql, clean_sql

def test_clean_sql_markdown_fences():
    raw = "```sql\nSELECT * FROM customers;\n```"
    assert clean_sql(raw) == "SELECT * FROM customers"

def test_clean_sql_plain():
    raw = "SELECT count(*) FROM orders;"
    assert clean_sql(raw) == "SELECT count(*) FROM orders"

def test_valid_select_query():
    sql = "SELECT customer_id, customer_city FROM customers WHERE customer_state = 'SP' LIMIT 10;"
    valid, err, cleaned = validate_sql(sql)
    assert valid is True
    assert err is None
    assert cleaned.startswith("SELECT")

def test_block_drop_table():
    sql = "DROP TABLE customers;"
    valid, err, _ = validate_sql(sql)
    assert valid is False
    assert "Only SELECT" in err

def test_block_insert():
    sql = "INSERT INTO customers (customer_id) VALUES ('test');"
    valid, err, _ = validate_sql(sql)
    assert valid is False
    assert "Only SELECT" in err

def test_block_update():
    sql = "UPDATE customers SET customer_city = 'hacked' WHERE customer_id = '1';"
    valid, err, _ = validate_sql(sql)
    assert valid is False
    assert "Only SELECT" in err

def test_block_delete():
    sql = "DELETE FROM orders WHERE order_status = 'canceled';"
    valid, err, _ = validate_sql(sql)
    assert valid is False
    assert "Only SELECT" in err

def test_block_multi_statement():
    sql = "SELECT * FROM orders; DROP TABLE customers;"
    valid, err, _ = validate_sql(sql)
    assert valid is False
    assert "Multiple SQL statements" in err

def test_block_empty_sql():
    valid, err, _ = validate_sql("")
    assert valid is False
    assert "empty" in err.lower()
