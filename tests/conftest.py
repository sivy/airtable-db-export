""" """

import pytest


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
