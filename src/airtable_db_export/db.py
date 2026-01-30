import typing as t
import duckdb
from contextlib import contextmanager
from pathlib import Path

import re


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
) -> None:
    """
    Bootstrap the database with the create table files
    """
    with dbconn(dbfile) as conn:
        for schema in schemas:
            with open(f"{data_dir}/create_{schema['sqltable']}.sql", "r") as f:
                conn.sql(f.read())


def make_table_create(schema: t.Dict[str, t.Any]) -> str:
    """
    Make SQL create table statement from schema

    schema: schema dictionary
    """
    table: dict[str, t.Any] = schema["sqltable"]

    stmt: str = f"CREATE TABLE IF NOT EXISTS {table}\n"
    coldefs: list[str] = []
    for col in schema["columns"]:
        if "sqlcolumn" in col:
            xtra: str = col.get("extra", "")
            coldefs.append(f"{col['sqlcolumn']} {col['sqltype']} {xtra}")

    return stmt + "(" + ",\n".join(coldefs) + ");"


def make_create_files(
    schemas: t.List[t.Dict[str, t.Any]],
    sql_dir: Path | str = "create_sql",
) -> None:
    """
    Make SQL create table statements from schemas
    """
    for create_schema in schemas:
        create_sql: str = make_table_create(create_schema)
        with open(f"{sql_dir}/create_{create_schema['sqltable']}.sql", "w") as sqlfile:
            sqlfile.write(create_sql)


def load_db(
    dbfile: Path | str,
    schemas: t.List[dict],
    data_dir: Path | str = "data",
) -> None:
    with dbconn(dbfile) as conn:
        for schema in schemas:
            print(
                f"Loading table {schema['sqltable']} from {data_dir}/{schema['sqltable']}.json"
            )
            sql: str = (
                f"INSERT INTO {schema['sqltable']}\n"
                f"SELECT * "
                f"FROM read_json('{data_dir}/{schema['sqltable']}.json');"
            )
            conn.sql(sql)
