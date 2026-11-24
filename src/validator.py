import re
import sqlite3
from typing import Tuple, Optional
import sqlglot
from sqlglot import exp

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "replace", "upsert", "attach", "detach", "vacuum", "reindex",
    "pragma", "grant", "revoke", "commit", "rollback", "savepoint"
}

FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Pragma
)

FORBIDDEN_FUNCTIONS = {
    "load_extension", "writefile", "readfile", "edit", "fts3_tokenizer"
}

def clean_sql(raw_sql: str) -> str:
    cleaned = raw_sql.strip()
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned

def validate_sql(raw_sql: str, db_path: Optional[str] = None) -> Tuple[bool, Optional[str], str]:
    sql = clean_sql(raw_sql)
    if not sql:
        return False, "SQL query is empty.", ""

    try:
        parsed_statements = sqlglot.parse(sql, read="sqlite")
    except Exception as e:
        return False, f"SQL parse error: {str(e)}", sql

    if not parsed_statements:
        return False, "Failed to parse any valid SQL statement.", sql

    if len(parsed_statements) > 1:
        return False, "Multiple SQL statements are not permitted.", sql

    statement = parsed_statements[0]
    if not isinstance(statement, exp.Select):
        return False, "Only SELECT statements are permitted.", sql

    for node in statement.walk():
        if isinstance(node, FORBIDDEN_EXPRESSIONS):
            return False, f"Disallowed SQL expression detected: {node.__class__.__name__}", sql
        if isinstance(node, exp.Anonymous):
            func_name = node.this.lower()
            if func_name in FORBIDDEN_FUNCTIONS:
                return False, f"Disallowed function call detected: {func_name}", sql

    tokens = [tok.text.lower() for tok in sqlglot.tokenize(sql, read="sqlite")]
    for token in tokens:
        if token in FORBIDDEN_KEYWORDS:
            if token == "replace" or token == "create":
                return False, f"Forbidden keyword detected: {token.upper()}", sql

    if db_path:
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {sql}")
            plan = cursor.fetchall()
            conn.close()
            for row in plan:
                op = row[1].lower() if len(row) > 1 else ""
                if op == "openwrite":
                    db_idx = row[3] if len(row) > 3 else 0
                    if db_idx == 0:
                        return False, "Unsafe execution plan: write operation on database table.", sql
        except Exception as e:
            return False, f"Execution plan validation failed: {str(e)}", sql

    return True, None, sql
