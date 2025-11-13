import csv
from collections.abc import KeysView
import json
import typing as t
from pathlib import Path

import duckdb
import pandas as pd
import yaml


def load_config(path: Path | str) -> dict:
    """
    Load config file
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_schemas(path: Path | str = "schemas.json") -> list[dict[str, t.Any]]:
    """
    Load schemas from schemas.json file
    """
    return json.load(open(path, "r"))


def load_dataframe(conn: duckdb.DuckDBPyConnection, path: str) -> pd.DataFrame:
    """
    Load data from Duckdb connection.
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


def save_table_json(data: list[dict], path: str) -> None:
    """
    Save table data to a JSON file.
    """
    if not path.endswith(".json"):
        path += ".json"

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_table_csv(data: list[dict], path: str) -> None:
    """
    Save table data to a CSV file.
    """
    if not path.endswith(".csv"):
        path += ".csv"

    if not data:
        # Create an empty CSV file if no data
        with open(path, "w") as f:
            pass
        return

    fieldnames: KeysView = data[0].keys()

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows(data)
