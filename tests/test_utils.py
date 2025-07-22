import pytest
from airtable_db_export.utils import load_config


def test_load_config(test_config_file):
    config = load_config(test_config_file)
    assert type(config) is dict
    for k in [
        "base_dir",
        "schemas_file",
        "datadir",
        "sql_dir",
        "db_file",
        "column_filters",
    ]:
        assert k in config.keys()
