import os
import sqlite3
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd

def get_connection(db_path: str = "olist.db") -> sqlite3.Connection:
    abs_path = Path(db_path).resolve()
    if not abs_path.exists():
        raise FileNotFoundError(f"Database file not found: {abs_path}")
    conn = sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(sql: str, db_path: str = "olist.db") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    conn = None
    try:
        conn = get_connection(db_path)
        df = pd.read_sql_query(sql, conn)
        return df, None
    except Exception as e:
        return None, str(e)
    finally:
        if conn:
            conn.close()

def get_database_schema(db_path: str = "olist.db") -> str:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    schema_lines = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        col_strs = [f"{col[1]} ({col[2]})" for col in columns]
        schema_lines.append(f"Table: {table}\n  Columns: {', '.join(col_strs)}")

        cursor.execute(f"SELECT * FROM {table} LIMIT 2;")
        samples = cursor.fetchall()
        if samples:
            sample_rows = [str(dict(sample)) for sample in samples]
            schema_lines.append(f"  Sample rows:\n    " + "\n    ".join(sample_rows))
        schema_lines.append("")

    conn.close()
    return "\n".join(schema_lines)
