from airtable_db_export import at
from pyairtable.models import schema as schemas
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


field_type_params = [
    ("singleLineText", "single", "name", "VARCHAR"),
    ("multiLineText", "name", "name", "VARCHAR"),
    ("richText", "name", "name_md", "VARCHAR"),
    ("multipleSelects", "multi select", "multi_select", "TEXT[]"),
    ("singleSelect", "single select", "single_select", "VARCHAR"),
    ("multipleRecordLinks", "multiple links", "multiple_links_ids", "TEXT[]"),
    ("singleRecordLink", "single link", "single_link_id", "VARCHAR"),
    ("autoNumber", "autonumber", "autonumber", "INTEGER"),
]


@pytest.mark.parametrize(
    "fixt,name,expected_sqlcol,expected_sqltype",
    field_type_params,
)
def test_sql_col_and_types(load_field, fixt, name, expected_sqlcol, expected_sqltype):
    field = load_field(fixt)

    col_map: dict[str, str] = {
        # field.name: name,
    }
    sqlcol, sqltype = at.get_sqlcol_and_type(col_map, field)
    print(f"{sqlcol} == {expected_sqlcol}", f"{sqltype} == {expected_sqltype}")
    assert sqlcol == expected_sqlcol
    assert sqltype == expected_sqltype


@pytest.mark.parametrize(
    "fixt,name,expected_sqlcol,expected_sqltype",
    field_type_params,
)
def test_sql_col_and_types_lookups(
    load_field, fixt, name, expected_sqlcol, expected_sqltype
):
    target_field = load_field(fixt)
    lookup_field = load_field("multipleLookupValues")

    tf_data = target_field.model_dump()
    # del tf_data["name"]
    lookup_field.name = target_field.name
    print(tf_data)
    lookup_field.options.result = schemas.parse_field_schema(tf_data)

    col_map: dict[str, str] = {
        # field.name: name,
    }
    sqlcol, sqltype = at.get_sqlcol_and_type(col_map, lookup_field)
    print(f"{expected_sqlcol=} → {sqlcol=} {expected_sqltype=} → {sqltype=}")
    assert sqlcol == expected_sqlcol
    assert sqltype == expected_sqltype
