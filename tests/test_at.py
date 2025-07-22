from airtable_db_export import at
import pytest


@pytest.mark.parametrize(
    "before,after",
    [
        ("Foo", "foo"),
        ("(Foo)", "foo"),
        ("Foo_bar", "foo_bar"),
        ("Foo bar", "foo_bar"),
    ],
)
def test_clean_name(before, after):
    assert after == at.clean_name(before)
