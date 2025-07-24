import typing as t
import yaml
import pandas as pd
import json
import duckdb
from pathlib import Path


###
def load_config(path: Path | str) -> dict:
    """
    Load config file
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_schemas(path: Path | str = "schemas.json") -> list[dict[str, t.Any]]:
    return json.load(open(path, "r"))


def load_dataframe(conn: duckdb.DuckDBPyConnection, path: str) -> pd.DataFrame:
    """
    Load data from Duckdb
    """
    with open(path, "r") as sql:
        stmt: str = sql.read()
        df = conn.sql(stmt).to_df()

    return df


def load_data(conn: duckdb.DuckDBPyConnection, path: str) -> duckdb.DuckDBPyRelation:
    """
    Load data from Duckdb
    """
    with open(path, "r") as sql:
        stmt: str = sql.read()
        rel = conn.sql(stmt)

    return rel
