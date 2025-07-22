from airtable_db_export import utils

TEST_CONF_FILE = "tests/fixtures/config.yml"


def test_load_config():
    config = utils.load_config(TEST_CONF_FILE)

    assert config

    assert isinstance(config, dict)

    assert "base_dir" in config
