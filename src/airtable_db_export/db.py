import typing as t
import duckdb
from contextlib import contextmanager
from pathlib import Path
import logging

import re

from airtable_db_export import backends

logger = logging.getLogger(__name__)


###
def clean_name(name: str):
    name = name.lower()
    name = re.sub(r"[^a-zA-Z0-9\s]+", "", name)
    name = re.sub(r"[\s]+", "_", name)
    return name


@contextmanager
def dbconn(dbfile: Path | str):
    conn = duckdb.connect(dbfile)
    yield conn
    conn.close()


def bootstrap_db(
    dbfile: Path | str,
    schemas: t.List[dict],
    data_dir: Path | str = "sql",
    backend: str = "duckdb",
) -> None:
    """
    Bootstrap the database with the create table files.

    Args:
        dbfile: Path to database file
        schemas: List of table schemas
        data_dir: Directory containing SQL CREATE files
        backend: Database backend ("duckdb" or "sqlite")
    """
    adapter = backends.get_adapter(backend)
    conn = adapter.connect(dbfile)
    try:
        for schema in schemas:
            sql_file = f"{data_dir}/create_{schema['sqltable']}.sql"
            with open(sql_file, "r") as f:
                sql = f.read()
            adapter.execute_sql(conn, sql)
            logger.info(f"Created table {schema['sqltable']}")
    finally:
        adapter.close(conn)


def make_table_create(schema: t.Dict[str, t.Any], backend: str = "duckdb") -> str:
    """
    Make SQL create table statement from schema.

    Args:
        schema: Table schema dictionary
        backend: Database backend ("duckdb" or "sqlite")

    Returns:
        SQL CREATE TABLE statement
    """
    table: dict[str, t.Any] = schema["sqltable"]

    stmt: str = f"CREATE TABLE IF NOT EXISTS {table}\n"
    coldefs: list[str] = []
    for col in schema["columns"]:
        if "sqlcolumn" in col:
            xtra: str = col.get("extra", "")
            sqltype: str = col["sqltype"]

            # Adjust SQL type for SQLite if needed
            if backend == "sqlite":
                # SQLite doesn't support FLOAT, use REAL instead
                sqltype = sqltype.replace("FLOAT", "REAL")

            coldefs.append(f"{col['sqlcolumn']} {sqltype} {xtra}")

    return stmt + "(" + ",\n".join(coldefs) + ");"


def make_create_files(
    schemas: t.List[t.Dict[str, t.Any]],
    sql_dir: Path | str = "create_sql",
    backend: str = "duckdb",
) -> None:
    """
    Make SQL create table statements from schemas.

    Args:
        schemas: List of table schemas
        sql_dir: Directory to write SQL files to
        backend: Database backend ("duckdb" or "sqlite")
    """
    for create_schema in schemas:
        create_sql: str = make_table_create(create_schema, backend)
        with open(f"{sql_dir}/create_{create_schema['sqltable']}.sql", "w") as sqlfile:
            sqlfile.write(create_sql)
        logger.info(f"Generated SQL for table {create_schema['sqltable']}")


def load_db(
    dbfile: Path | str,
    schemas: t.List[dict],
    data_dir: Path | str = "data",
    backend: str = "duckdb",
) -> None:
    """
    Load JSON data into database tables.

    Args:
        dbfile: Path to database file
        schemas: List of table schemas
        data_dir: Directory containing JSON data files
        backend: Database backend ("duckdb" or "sqlite")
    """
    adapter = backends.get_adapter(backend)
    conn = adapter.connect(dbfile)
    try:
        for schema in schemas:
            json_file = f"{data_dir}/{schema['sqltable']}.json"
            adapter.execute_insert_from_json(
                conn, schema["sqltable"], json_file, schema
            )
    finally:
        adapter.close(conn)
