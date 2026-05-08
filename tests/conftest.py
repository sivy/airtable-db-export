""" """

import pytest
from pathlib import Path
import json
from pyairtable.models import schema as schemas


def load_sample_data(path: Path | str):
    path: Path = Path(path)
    data = {}
    for dirpath, dirnames, filenames in path.walk():
        for fname in filenames:
            if fname.startswith("."):
                continue
            d = Path(dirpath)
            fname = Path(fname)
            ftype = fname.stem
            with open(d / fname, "r") as f:
                loaded = json.load(f)
                data[ftype] = loaded

    return data


@pytest.fixture
def test_config_file(tmp_path):
    config_path = tmp_path / "config.yml"
    with open(config_path, "w") as f:
        f.write("""
        base_dir: generated
        schemas_file: schemas.json
        datadir: data
        sql_dir: create_sql
        db_file: example.duckdb
        column_filters:
        - " copy$"
        - "(deleteme)"
        """)
    return config_path


@pytest.fixture
def load_field():
    sample_data = load_sample_data("./tests/sample_data")

    def _load_field(fixt):
        return schemas.parse_field_schema(sample_data[fixt])

    return _load_field


@pytest.fixture
def sample_json_data(tmp_path):
    """Create a sample JSON data file for database loading tests."""
    data = [
        {
            "id": "rec001",
            "name": "Widget A",
            "quantity": 10,
            "active": True,
            "tags": ["red", "medium"],
            "category": "hardware",
        },
        {
            "id": "rec002",
            "name": "Widget B",
            "quantity": 5,
            "active": False,
            "tags": ["blue"],
            "category": "software",
        },
        {
            "id": "rec003",
            "name": "Widget C",
            "quantity": None,
            "active": None,
            "tags": [],
            "category": None,
        },
    ]

    data_file = tmp_path / "widgets.json"
    with open(data_file, "w") as f:
        json.dump(data, f)

    return data_file


@pytest.fixture
def sample_schema():
    """Return a sample schema dict for database tests."""
    return {
        "sqltable": "widgets",
        "columns": [
            {
                "field": None,
                "sqlcolumn": "id",
                "sqltype": "varchar",
                "extra": "primary key",
            },
            {
                "field": "Name",
                "sqlcolumn": "name",
                "sqltype": "VARCHAR",
                "extra": "",
            },
            {
                "field": "Quantity",
                "sqlcolumn": "quantity",
                "sqltype": "INTEGER",
                "extra": "",
            },
            {
                "field": "Active",
                "sqlcolumn": "active",
                "sqltype": "BOOLEAN",
                "extra": "",
            },
            {
                "field": "Tags",
                "sqlcolumn": "tags",
                "sqltype": "TEXT[]",
                "extra": "",
            },
            {
                "field": "Category",
                "sqlcolumn": "category",
                "sqltype": "VARCHAR",
                "extra": "",
            },
        ],
    }


@pytest.fixture
def sample_schema_sqlite():
    """Return a sample schema dict for SQLite database tests."""
    return {
        "sqltable": "widgets",
        "columns": [
            {
                "field": None,
                "sqlcolumn": "id",
                "sqltype": "varchar",
                "extra": "primary key",
            },
            {
                "field": "Name",
                "sqlcolumn": "name",
                "sqltype": "TEXT",
                "extra": "",
            },
            {
                "field": "Quantity",
                "sqlcolumn": "quantity",
                "sqltype": "INTEGER",
                "extra": "",
            },
            {
                "field": "Active",
                "sqlcolumn": "active",
                "sqltype": "INTEGER",  # SQLite: 0 or 1
                "extra": "",
            },
            {
                "field": "Tags",
                "sqlcolumn": "tags",
                "sqltype": "TEXT",  # SQLite: JSON string
                "extra": "",
            },
            {
                "field": "Category",
                "sqlcolumn": "category",
                "sqltype": "TEXT",
                "extra": "",
            },
        ],
    }
