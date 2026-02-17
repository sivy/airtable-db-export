from airtable_db_export import at
from pyairtable.models import schema as schemas
import pytest
import typing as t


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


field_type_params = [
    # col_config, fixture, field_name, result
    # defaults
    (None, "singleLineText", "single text", ["single_text", "VARCHAR", False]),
    (None, "multiLineText", "multi text", ["multi_text", "VARCHAR", False]),
    (None, "richText", "rich text", ["rich_text_md", "VARCHAR", False]),
    (None, "multipleSelects", "multi select", ["multi_select", "TEXT[]", False]),
    (None, "singleSelect", "single select", ["single_select", "VARCHAR", False]),
    (
        None,
        "multipleRecordLinks",
        "multiple links",
        ["multiple_links_ids", "TEXT[]", False],
    ),
    (None, "singleRecordLink", "single link", ["single_link_id", "VARCHAR", False]),
    (None, "autoNumber", "autonumber", ["autonumber", "INTEGER", False]),
    # user specified
    (
        {
            "sqlcol": "user_multi_select_col",
            "sqltype": "VARCHAR",
        },
        "multipleSelects",
        "multi select",
        ["user_multi_select_col", "VARCHAR", True],
    ),
    (
        {
            "sqlcol": "user_multi_record_col",
            "sqltype": "VARCHAR",
        },
        "multipleRecordLinks",
        "multiple links",
        ["user_multi_record_col", "VARCHAR", True],
    ),
]


@pytest.mark.parametrize(
    "col_config,fixture,field_name,result",
    field_type_params,
)
def test_sql_col_and_types(load_field, col_config, fixture, field_name, result):
    field = load_field(fixture)

    col_map: dict[str, str] = {field_name: col_config} if col_config else {}

    sqlcol, sqltype, user_specified = at.get_sqlcol_and_type(col_map, field)
    assert result == [sqlcol, sqltype, user_specified]


@pytest.mark.parametrize(
    "col_config,fixture,field_name,result",
    field_type_params,
)
def test_sql_col_and_types_lookups(load_field, col_config, fixture, field_name, result):
    """
    Lookup fields should be stored according to the target field?

    IE if a Lookup field gets a value from a number field, the type
    should be a number; same for a date or text field.

    """
    target_field = load_field(fixture)
    lookup_field = load_field("multipleLookupValues")

    tf_data = target_field.model_dump()
    lookup_field.name = target_field.name
    lookup_field.options.result = schemas.parse_field_schema(tf_data)

    col_map: dict[str, t.Any] = {field_name: col_config} if col_config else {}

    sqlcol, sqltype, user_specified = at.get_sqlcol_and_type(col_map, lookup_field)
    assert result == [sqlcol, sqltype, user_specified]
