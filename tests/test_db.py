import pytest
import sqlite3
from src.db import get_database_schema, execute_query, get_connection

def test_get_connection_readonly():
    conn = get_connection("olist.db")
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM customers;")
    count = cursor.fetchone()[0]
    assert count > 0
    with pytest.raises(sqlite3.OperationalError):
        cursor.execute("CREATE TABLE test_mut (id INT);")
    conn.close()

def test_get_database_schema():
    schema = get_database_schema("olist.db")
    assert "Table: customers" in schema
    assert "Table: orders" in schema
    assert "Table: order_items" in schema
    assert "Columns:" in schema

def test_execute_query_success():
    df, err = execute_query("SELECT count(*) AS total FROM orders;", "olist.db")
    assert err is None
    assert df is not None
    assert len(df) == 1
    assert "total" in df.columns

def test_execute_query_syntax_error():
    df, err = execute_query("SELECT FROM INVALID_SYNTAX;", "olist.db")
    assert df is None
    assert err is not None
