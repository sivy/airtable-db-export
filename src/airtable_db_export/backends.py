"""
Database backend support for ADBE.

Supports multiple SQL database backends (DuckDB, SQLite) with unified interface.
"""

import typing as t
from pathlib import Path
from contextlib import contextmanager
import json
import logging

logger = logging.getLogger(__name__)

# Supported backends
BACKENDS = ["duckdb", "sqlite"]

# Type mappings per backend
TYPEMAP_DUCKDB: dict[str, str] = {
    "autoNumber": "INTEGER",
    "checkbox": "BOOLEAN",
    "count": "INTEGER",
    "currency": "FLOAT",
    "dateTime": "TIMESTAMP",
    "email": "VARCHAR",
    "multilineText": "VARCHAR",
    "richText": "VARCHAR",
    "multiLineText": "VARCHAR",
    "multipleSelects": "TEXT[]",
    "multipleLookupValues": "TEXT[]",
    "multipleRecordLinks": "TEXT[]",
    "number": "INTEGER",
    "singleLineText": "VARCHAR",
    "singleSelect": "VARCHAR",
    "singleRecordLink": "VARCHAR",
    "formula": "VARCHAR",
}

TYPEMAP_SQLITE: dict[str, str] = {
    "autoNumber": "INTEGER",
    "checkbox": "INTEGER",  # SQLite: 0 or 1
    "count": "INTEGER",
    "currency": "REAL",  # SQLite: REAL instead of FLOAT
    "dateTime": "TEXT",  # SQLite: timestamps as text or integer
    "email": "TEXT",
    "multilineText": "TEXT",
    "richText": "TEXT",
    "multiLineText": "TEXT",
    "multipleSelects": "TEXT",  # JSON string
    "multipleLookupValues": "TEXT",  # JSON string
    "multipleRecordLinks": "TEXT",  # JSON string
    "number": "INTEGER",
    "singleLineText": "TEXT",
    "singleSelect": "TEXT",
    "singleRecordLink": "TEXT",
    "formula": "TEXT",
}


def detect_backend(db_file: str | Path) -> str:
    """
    Detect database backend from file extension.

    Returns:
        "duckdb" or "sqlite"

    Raises:
        ValueError: If extension is ambiguous (.db, .db3, etc.)
    """
    path = Path(db_file)
    suffix = path.suffix.lower()

    if suffix == ".duckdb":
        return "duckdb"
    elif suffix == ".sqlite":
        return "sqlite"
    elif suffix in [".db", ".db3", ".sqlite3"]:
        raise ValueError(
            f"Ambiguous database extension '{suffix}'. "
            f"Use --backend flag to specify 'sqlite' or 'duckdb', "
            f"or rename database file with explicit extension (.sqlite or .duckdb)."
        )
    else:
        # Default to duckdb for unknown extensions
        logger.info(f"Unknown database extension '{suffix}', defaulting to duckdb")
        return "duckdb"


def validate_backend(backend: str) -> str:
    """
    Validate that backend is supported.

    Returns:
        backend (normalized)

    Raises:
        ValueError: If backend not supported
    """
    backend_lower = backend.lower()
    if backend_lower not in BACKENDS:
        raise ValueError(
            f"Unsupported backend '{backend}'. "
            f"Supported backends: {', '.join(BACKENDS)}"
        )
    return backend_lower


def get_typemap(backend: str) -> dict[str, str]:
    """
    Get type mapping for backend.

    Args:
        backend: "duckdb" or "sqlite"

    Returns:
        Type mapping dict (Airtable type → SQL type)
    """
    backend = validate_backend(backend)
    if backend == "duckdb":
        return TYPEMAP_DUCKDB
    else:  # sqlite
        return TYPEMAP_SQLITE


def sql_type_for_airtable(airtable_type: str, backend: str) -> str:
    """
    Get SQL type for an Airtable field type on given backend.

    Args:
        airtable_type: Airtable field type (e.g., "singleLineText")
        backend: "duckdb" or "sqlite"

    Returns:
        SQL type (e.g., "VARCHAR", "TEXT")
    """
    typemap = get_typemap(backend)
    return typemap.get(airtable_type, "TEXT")


class DatabaseAdapter:
    """Base adapter for database operations."""

    def connect(self, db_file: str | Path):
        """Open database connection."""
        raise NotImplementedError

    def close(self, conn):
        """Close database connection."""
        raise NotImplementedError

    def execute_sql(self, conn, sql: str):
        """Execute raw SQL statement."""
        raise NotImplementedError

    def execute_insert_from_json(
        self, conn, table: str, json_file: str | Path, schema: dict
    ):
        """Load JSON data into table."""
        raise NotImplementedError


class DuckDBAdapter(DatabaseAdapter):
    """Adapter for DuckDB backend."""

    def connect(self, db_file: str | Path):
        """Open DuckDB connection."""
        import duckdb

        return duckdb.connect(str(db_file))

    def close(self, conn):
        """Close DuckDB connection."""
        if conn:
            conn.close()

    def execute_sql(self, conn, sql: str):
        """Execute SQL using DuckDB."""
        return conn.sql(sql)

    def execute_insert_from_json(
        self, conn, table: str, json_file: str | Path, schema: dict
    ):
        """Load JSON using DuckDB's native read_json()."""
        sql = f"INSERT INTO {table}\nSELECT * FROM read_json('{json_file}');"
        conn.sql(sql)
        logger.info(f"Loaded {table} from {json_file}")


class SQLiteAdapter(DatabaseAdapter):
    """Adapter for SQLite backend."""

    def connect(self, db_file: str | Path):
        """Open SQLite connection."""
        import sqlite3

        return sqlite3.connect(str(db_file))

    def close(self, conn):
        """Close SQLite connection."""
        if conn:
            conn.close()

    def execute_sql(self, conn, sql: str):
        """Execute SQL using SQLite."""
        # Handle multiple statements separated by ;
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
        conn.commit()

    def execute_insert_from_json(
        self, conn, table: str, json_file: str | Path, schema: dict
    ):
        """Load JSON by parsing in Python and using executemany()."""
        import sqlite3

        with open(json_file, "r") as f:
            data = json.load(f)

        if not data:
            logger.info(f"No data in {json_file}")
            return

        # Build column list from schema
        columns = []
        column_types = {}
        for col_def in schema.get("columns", []):
            if "sqlcolumn" in col_def:
                columns.append(col_def["sqlcolumn"])
                column_types[col_def["sqlcolumn"]] = col_def.get("sqltype", "TEXT")

        if not columns:
            raise ValueError(f"No columns defined in schema for table {table}")

        # Transform rows: serialize arrays, convert booleans
        rows = []
        for row in data:
            transformed_row = []
            for col in columns:
                value = row.get(col)

                # Handle None
                if value is None:
                    transformed_row.append(None)
                # Serialize arrays as JSON strings
                elif isinstance(value, list):
                    transformed_row.append(json.dumps(value))
                # Convert booleans to 0/1
                elif isinstance(value, bool):
                    transformed_row.append(1 if value else 0)
                else:
                    transformed_row.append(value)

            rows.append(tuple(transformed_row))

        # Build INSERT statement
        placeholders = ", ".join(["?"] * len(columns))
        col_list = ", ".join(columns)
        insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        # Insert all rows
        cursor = conn.cursor()
        cursor.executemany(insert_sql, rows)
        conn.commit()

        logger.info(f"Loaded {len(rows)} rows into {table} from {json_file}")


def get_adapter(backend: str) -> DatabaseAdapter:
    """
    Get database adapter for backend.

    Args:
        backend: "duckdb" or "sqlite"

    Returns:
        DatabaseAdapter instance

    Raises:
        ValueError: If backend not supported
    """
    backend = validate_backend(backend)
    if backend == "duckdb":
        return DuckDBAdapter()
    else:  # sqlite
        return SQLiteAdapter()
