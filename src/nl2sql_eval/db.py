import sqlite3
from pathlib import Path


def build_database(schema_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(Path(schema_path).read_text())
    conn.commit()
    return conn


def execute_query(conn: sqlite3.Connection, sql: str) -> list[tuple] | None:
    try:
        return conn.execute(sql).fetchall()
    except sqlite3.Error:
        return None
