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
                print(d / fname)
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
