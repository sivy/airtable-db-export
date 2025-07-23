from airtable_db_export import utils


def test_load_config(test_config_file):
    config = utils.load_config(test_config_file)

    assert config

    assert isinstance(config, dict)

    assert "base_dir" in config
