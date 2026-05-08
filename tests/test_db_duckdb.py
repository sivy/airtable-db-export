"""Tests for DuckDB database operations (regression suite)."""

import json
import pytest
import duckdb
from pathlib import Path

from airtable_db_export import backends, db


class TestDuckDBAdapterConnection:
    """Test DuckDB connection management."""

    def test_connect_creates_connection(self, tmp_path):
        """Should create a DuckDB connection."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()

        conn = adapter.connect(db_file)
        try:
            assert conn is not None
            assert isinstance(conn, duckdb.DuckDBPyConnection)
        finally:
            adapter.close(conn)

    def test_connect_creates_file(self, tmp_path):
        """Should create the database file on disk."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()

        conn = adapter.connect(db_file)
        adapter.close(conn)

        assert db_file.exists()

    def test_close_connection(self, tmp_path):
        """Should close connection without error."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()

        conn = adapter.connect(db_file)
        adapter.close(conn)  # Should not raise


class TestDuckDBAdapterExecute:
    """Test SQL execution via DuckDB adapter."""

    def test_execute_create_table(self, tmp_path):
        """Should execute CREATE TABLE statement."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn, "CREATE TABLE test (id VARCHAR PRIMARY KEY, name VARCHAR)"
            )

            # Verify table exists
            result = conn.sql("SHOW TABLES").fetchall()
            tables = [row[0] for row in result]
            assert "test" in tables
        finally:
            adapter.close(conn)

    def test_execute_insert_and_select(self, tmp_path):
        """Should execute INSERT and SELECT."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn, "CREATE TABLE test (id VARCHAR PRIMARY KEY, name VARCHAR)"
            )
            adapter.execute_sql(
                conn, "INSERT INTO test (id, name) VALUES ('rec1', 'Widget A')"
            )

            result = conn.sql("SELECT * FROM test").fetchall()
            assert len(result) == 1
            assert result[0][0] == "rec1"
            assert result[0][1] == "Widget A"
        finally:
            adapter.close(conn)


class TestDuckDBAdapterLoadJson:
    """Test JSON loading via DuckDB adapter."""

    def test_load_simple_json(self, tmp_path, sample_json_data, sample_schema):
        """Should load JSON data using read_json()."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn,
                "CREATE TABLE IF NOT EXISTS widgets (id VARCHAR PRIMARY KEY, name VARCHAR, "
                "quantity INTEGER, active BOOLEAN, tags TEXT[], category VARCHAR)",
            )

            adapter.execute_insert_from_json(
                conn, "widgets", str(sample_json_data), sample_schema
            )

            result = conn.sql("SELECT * FROM widgets ORDER BY id").fetchall()
            assert len(result) == 3
            assert result[0][0] == "rec001"
            assert result[0][1] == "Widget A"
            assert result[0][2] == 10
        finally:
            adapter.close(conn)

    def test_load_json_booleans(self, tmp_path, sample_json_data, sample_schema):
        """Should load booleans as native DuckDB BOOLEAN."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn,
                "CREATE TABLE IF NOT EXISTS widgets (id VARCHAR PRIMARY KEY, name VARCHAR, "
                "quantity INTEGER, active BOOLEAN, tags TEXT[], category VARCHAR)",
            )
            adapter.execute_insert_from_json(
                conn, "widgets", str(sample_json_data), sample_schema
            )

            result = conn.sql("SELECT id, active FROM widgets ORDER BY id").fetchall()
            # rec001: active=True
            assert result[0][1] is True
            # rec002: active=False
            assert result[1][1] is False
            # rec003: active=None
            assert result[2][1] is None
        finally:
            adapter.close(conn)

    def test_load_json_arrays(self, tmp_path, sample_json_data, sample_schema):
        """Should load arrays as native DuckDB TEXT[]."""
        db_file = tmp_path / "test.duckdb"
        adapter = backends.DuckDBAdapter()
        conn = adapter.connect(db_file)

        try:
            adapter.execute_sql(
                conn,
                "CREATE TABLE IF NOT EXISTS widgets (id VARCHAR PRIMARY KEY, name VARCHAR, "
                "quantity INTEGER, active BOOLEAN, tags TEXT[], category VARCHAR)",
            )
            adapter.execute_insert_from_json(
                conn, "widgets", str(sample_json_data), sample_schema
            )

            result = conn.sql("SELECT id, tags FROM widgets ORDER BY id").fetchall()
            # rec001: tags=["red", "medium"] → native array
            assert result[0][1] == ["red", "medium"]
            # rec002: tags=["blue"]
            assert result[1][1] == ["blue"]
        finally:
            adapter.close(conn)


class TestDbModuleDuckDB:
    """Test db module functions with DuckDB backend."""

    def test_make_table_create_duckdb(self, sample_schema):
        """Should generate DuckDB-compatible CREATE TABLE statement."""
        sql = db.make_table_create(sample_schema, backend="duckdb")

        assert "CREATE TABLE IF NOT EXISTS widgets" in sql
        assert "BOOLEAN" in sql
        assert "TEXT[]" in sql

    def test_bootstrap_db_duckdb(self, tmp_path, sample_schema):
        """Should create DuckDB tables from SQL files."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        db_file = tmp_path / "test.duckdb"

        # Write CREATE SQL file
        sql = db.make_table_create(sample_schema, backend="duckdb")
        sql_file = sql_dir / "create_widgets.sql"
        with open(sql_file, "w") as f:
            f.write(sql)

        # Bootstrap
        db.bootstrap_db(str(db_file), [sample_schema], str(sql_dir), backend="duckdb")

        # Verify table exists
        conn = duckdb.connect(str(db_file))
        result = conn.sql("SHOW TABLES").fetchall()
        conn.close()
        tables = [row[0] for row in result]
        assert "widgets" in tables

    def test_load_db_duckdb(self, tmp_path, sample_json_data, sample_schema):
        """Should load JSON data into DuckDB database."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()
        db_file = tmp_path / "test.duckdb"

        # Create table
        sql = db.make_table_create(sample_schema, backend="duckdb")
        sql_file = sql_dir / "create_widgets.sql"
        with open(sql_file, "w") as f:
            f.write(sql)
        db.bootstrap_db(str(db_file), [sample_schema], str(sql_dir), backend="duckdb")

        # Load data
        db.load_db(str(db_file), [sample_schema], str(tmp_path), backend="duckdb")

        # Verify data
        conn = duckdb.connect(str(db_file))
        result = conn.sql("SELECT COUNT(*) FROM widgets").fetchone()
        conn.close()
        assert result[0] == 3

    def test_make_create_files_duckdb(self, tmp_path, sample_schema):
        """Should generate SQL files for DuckDB."""
        sql_dir = tmp_path / "sql"
        sql_dir.mkdir()

        db.make_create_files([sample_schema], str(sql_dir), backend="duckdb")

        sql_file = sql_dir / "create_widgets.sql"
        assert sql_file.exists()
        content = sql_file.read_text()
        assert "CREATE TABLE IF NOT EXISTS widgets" in content
        assert "BOOLEAN" in content
