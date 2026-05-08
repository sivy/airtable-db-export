"""Tests for SQLite database operations."""

import json
import pytest
import sqlite3
from pathlib import Path

from airtable_db_export import backends, db


class TestSQLiteAdapterConnection:
    """Test SQLite connection management."""

    def test_connect_creates_database(self, tmp_path):
        """Should create a SQLite database file."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()

        conn = adapter.connect(db_file)
        try:
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)
        finally:
            adapter.close(conn)

    def test_connect_creates_file(self, tmp_path):
        """Should create the database file on disk."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()

        conn = adapter.connect(db_file)
        adapter.close(conn)

        assert db_file.exists()

    def test_close_connection(self, tmp_path):
        """Should close connection without error."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()

        conn = adapter.connect(db_file)
        adapter.close(conn)  # Should not raise


class TestSQLiteAdapterExecute:
    """Test SQL execution via SQLite adapter."""

    def test_execute_create_table(self, tmp_path):
        """Should execute CREATE TABLE statement."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn, "CREATE TABLE test (id TEXT PRIMARY KEY, name TEXT)"
            )

            # Verify table exists
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "test" in tables
        finally:
            adapter.close(conn)

    def test_execute_insert_and_select(self, tmp_path):
        """Should execute INSERT and SELECT."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn, "CREATE TABLE test (id TEXT PRIMARY KEY, name TEXT)"
            )
            adapter.execute_sql(
                conn, "INSERT INTO test (id, name) VALUES ('rec1', 'Widget A')"
            )

            cursor = conn.execute("SELECT * FROM test")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "rec1"
            assert rows[0][1] == "Widget A"
        finally:
            adapter.close(conn)

    def test_execute_multiple_statements(self, tmp_path):
        """Should handle statements with semicolons."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            # CREATE TABLE statement with trailing semicolon (from SQL files)
            sql = "CREATE TABLE IF NOT EXISTS test (id TEXT PRIMARY KEY, name TEXT);"
            adapter.execute_sql(conn, sql)

            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "test" in tables
        finally:
            adapter.close(conn)


class TestSQLiteAdapterLoadJson:
    """Test JSON loading via SQLite adapter."""

    def test_load_simple_json(self, tmp_path, sample_json_data, sample_schema_sqlite):
        """Should load JSON data into SQLite table."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            # Create table first
            adapter.execute_sql(
                conn,
                "CREATE TABLE widgets (id TEXT PRIMARY KEY, name TEXT, quantity INTEGER, "
                "active INTEGER, tags TEXT, category TEXT)",
            )

            # Load JSON data
            adapter.execute_insert_from_json(
                conn, "widgets", str(sample_json_data), sample_schema_sqlite
            )

            # Verify data
            cursor = conn.execute("SELECT * FROM widgets ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 3
            assert rows[0][0] == "rec001"
            assert rows[0][1] == "Widget A"
            assert rows[0][2] == 10
        finally:
            adapter.close(conn)

    def test_load_json_converts_booleans(
        self, tmp_path, sample_json_data, sample_schema_sqlite
    ):
        """Should convert Python booleans to 0/1 for SQLite."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn,
                "CREATE TABLE widgets (id TEXT PRIMARY KEY, name TEXT, quantity INTEGER, "
                "active INTEGER, tags TEXT, category TEXT)",
            )
            adapter.execute_insert_from_json(
                conn, "widgets", str(sample_json_data), sample_schema_sqlite
            )

            cursor = conn.execute("SELECT id, active FROM widgets ORDER BY id")
            rows = cursor.fetchall()
            # rec001: active=True → 1
            assert rows[0][1] == 1
            # rec002: active=False → 0
            assert rows[1][1] == 0
            # rec003: active=None → None
            assert rows[2][1] is None
        finally:
            adapter.close(conn)

    def test_load_json_serializes_arrays(
        self, tmp_path, sample_json_data, sample_schema_sqlite
    ):
        """Should serialize array values as JSON strings."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn,
                "CREATE TABLE widgets (id TEXT PRIMARY KEY, name TEXT, quantity INTEGER, "
                "active INTEGER, tags TEXT, category TEXT)",
            )
            adapter.execute_insert_from_json(
                conn, "widgets", str(sample_json_data), sample_schema_sqlite
            )

            cursor = conn.execute("SELECT id, tags FROM widgets ORDER BY id")
            rows = cursor.fetchall()
            # rec001: tags=["red", "medium"] → JSON string
            tags = json.loads(rows[0][1])
            assert tags == ["red", "medium"]
            # rec002: tags=["blue"] → JSON string
            tags = json.loads(rows[1][1])
            assert tags == ["blue"]
            # rec003: tags=[] → JSON string "[]"
            tags = json.loads(rows[2][1])
            assert tags == []
        finally:
            adapter.close(conn)

    def test_load_json_handles_nulls(
        self, tmp_path, sample_json_data, sample_schema_sqlite
    ):
        """Should handle None/null values correctly."""
        db_file = tmp_path / "test.sqlite"
        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn,
                "CREATE TABLE widgets (id TEXT PRIMARY KEY, name TEXT, quantity INTEGER, "
                "active INTEGER, tags TEXT, category TEXT)",
            )
            adapter.execute_insert_from_json(
                conn, "widgets", str(sample_json_data), sample_schema_sqlite
            )

            cursor = conn.execute(
                "SELECT id, quantity, category FROM widgets WHERE id='rec003'"
            )
            row = cursor.fetchone()
            assert row[1] is None  # quantity=None
            assert row[2] is None  # category=None
        finally:
            adapter.close(conn)

    def test_load_empty_json(self, tmp_path, sample_schema_sqlite):
        """Should handle empty JSON file without error."""
        db_file = tmp_path / "test.sqlite"
        empty_json = tmp_path / "empty.json"
        with open(empty_json, "w") as f:
            json.dump([], f)

        adapter = backends.SQLiteAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn,
                "CREATE TABLE widgets (id TEXT PRIMARY KEY, name TEXT)",
            )
            # Should not raise
            adapter.execute_insert_from_json(
                conn, "widgets", str(empty_json), sample_schema_sqlite
            )

            cursor = conn.execute("SELECT COUNT(*) FROM widgets")
            assert cursor.fetchone()[0] == 0
        finally:
            adapter.close(conn)


class TestDbModuleSQLite:
    """Test db module functions with SQLite backend."""

    def test_make_table_create_sqlite(self, sample_schema):
        """Should generate valid SQLite CREATE TABLE statement."""
        sql = db.make_table_create(sample_schema, backend="sqlite")

        assert "CREATE TABLE IF NOT EXISTS widgets" in sql
        # Should convert TEXT[] to TEXT (via schema's sqltype)
        # and FLOAT to REAL
        assert (
            "REAL" not in sql
        )  # No FLOAT → REAL conversion needed here (schema already has correct type)

    def test_make_table_create_duckdb(self, sample_schema):
        """Should generate valid DuckDB CREATE TABLE statement."""
        sql = db.make_table_create(sample_schema, backend="duckdb")

        assert "CREATE TABLE IF NOT EXISTS widgets" in sql
        assert "BOOLEAN" in sql
        assert "TEXT[]" in sql

    def test_make_table_create_sqlite_float_to_real(self):
        """Should convert FLOAT to REAL in SQLite DDL."""
        schema = {
            "sqltable": "prices",
            "columns": [
                {"sqlcolumn": "amount", "sqltype": "FLOAT", "extra": ""},
            ],
        }
        sql = db.make_table_create(schema, backend="sqlite")
        assert "REAL" in sql
        assert "FLOAT" not in sql

    def test_bootstrap_db_sqlite(self, tmp_path, sample_schema_sqlite):
        """Should create SQLite database tables from SQL files."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        db_file = tmp_path / "test.sqlite"

        # Write CREATE SQL file
        sql = db.make_table_create(sample_schema_sqlite, backend="sqlite")
        sql_file = sql_dir / "create_widgets.sql"
        with open(sql_file, "w") as f:
            f.write(sql)

        # Bootstrap
        db.bootstrap_db(
            str(db_file), [sample_schema_sqlite], str(sql_dir), backend="sqlite"
        )

        # Verify table exists
        conn = sqlite3.connect(str(db_file))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "widgets" in tables

    def test_load_db_sqlite(self, tmp_path, sample_json_data, sample_schema_sqlite):
        """Should load JSON data into SQLite database."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        db_file = tmp_path / "test.sqlite"

        # Create table
        sql = db.make_table_create(sample_schema_sqlite, backend="sqlite")
        sql_file = sql_dir / "create_widgets.sql"
        with open(sql_file, "w") as f:
            f.write(sql)
        db.bootstrap_db(
            str(db_file), [sample_schema_sqlite], str(sql_dir), backend="sqlite"
        )

        # Load data
        db.load_db(
            str(db_file), [sample_schema_sqlite], str(tmp_path), backend="sqlite"
        )

        # Verify data
        conn = sqlite3.connect(str(db_file))
        cursor = conn.execute("SELECT COUNT(*) FROM widgets")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 3
