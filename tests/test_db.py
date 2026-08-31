from pathlib import Path

from nl2sql_eval.db import build_database, execute_query

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "data" / "schema.sql"


def test_build_database_creates_expected_tables():
    conn = build_database(str(SCHEMA_PATH))
    assert execute_query(conn, "SELECT COUNT(*) FROM employees;") == [(5,)]


def test_execute_query_returns_none_on_error():
    conn = build_database(str(SCHEMA_PATH))
    assert execute_query(conn, "SELECT * FROM not_a_table;") is None
