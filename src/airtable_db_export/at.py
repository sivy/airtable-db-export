import json
import logging
import re
import typing as t
from collections import defaultdict
from pathlib import Path

from pyairtable.models import schema as schemas

if t.TYPE_CHECKING:
    from pyairtable import Api as ATApi
    from pyairtable.models.schema import FieldSchema


logger = logging.getLogger(__name__)


# Constants
class EXPORTS:
    JSON = "json"
    CSV = "csv"


class ATYPES:
    class ATYPE(str):
        pass

    SINGLE_LINE_TEXT: ATYPE = ATYPE("singleLineText")
    MULTI_LINE_TEXT: ATYPE = ATYPE("multilineText")
    RICH_TEXT: ATYPE = ATYPE("richText")

    SINGLE_SELECT: ATYPE = ATYPE("singleSelect")
    MULTI_SELECT: ATYPE = ATYPE("multipleSelects")
    MULTI_RECORD_LINK: ATYPE = ATYPE("multipleRecordLinks")
    SINGLE_RECORD_LINK: ATYPE = ATYPE("singleRecordLink")
    MULTI_LOOKUP: ATYPE = ATYPE("multipleLookupValues")
    SINGLE_LOOKUP: ATYPE = ATYPE("singleLookupValue")
    CHECKBOX: ATYPE = ATYPE("checkbox")
    DATE_TIME: ATYPE = ATYPE("dateTime")
    CURRENCY: ATYPE = ATYPE("currency")
    NUMBER: ATYPE = ATYPE("number")
    AUTO_NUMBER: ATYPE = ATYPE("autoNumber")
    FORMULA: ATYPE = ATYPE("formula")
    COUNT: ATYPE = ATYPE("count")
    EMAIL: ATYPE = ATYPE("email")


# Map Airtable types to SQL types
TYPEMAP: dict[ATYPES.ATYPE, str] = {
    ATYPES.AUTO_NUMBER: "INTEGER",
    ATYPES.CHECKBOX: "BOOLEAN",
    ATYPES.COUNT: "INTEGER",
    ATYPES.CURRENCY: "FLOAT",
    ATYPES.DATE_TIME: "TIMESTAMP",
    ATYPES.EMAIL: "VARCHAR",
    ATYPES.MULTI_LINE_TEXT: "VARCHAR",
    ATYPES.MULTI_LOOKUP: "TEXT[]",
    ATYPES.MULTI_RECORD_LINK: "TEXT[]",
    ATYPES.MULTI_SELECT: "TEXT[]",
    ATYPES.NUMBER: "INTEGER",
    ATYPES.RICH_TEXT: "VARCHAR",
    ATYPES.SINGLE_LINE_TEXT: "VARCHAR",
    ATYPES.SINGLE_LOOKUP: "VARCHAR",
    ATYPES.SINGLE_RECORD_LINK: "VARCHAR",
    ATYPES.SINGLE_SELECT: "VARCHAR",
}


###
def clean_name(name: str):
    """
    Clean names

    • lower-case
    • preserve alphanum, underscore, spaces
    • convert spaces to underscores
    """
    name = name.lower()
    name = re.sub(r"[^a-zA-Z0-9_\s]+", "", name)
    name = re.sub(r"[\s]+", "_", name)
    return name


def archive_schemas(api_client: "ATApi") -> None:
    """
    Archive the schemas of all Airtable bases to a JSON file.
    """
    import json

    ref_schema: dict[str, dict] = {}
    for base in api_client.bases():
        ref_schema[base.id] = base.schema().model_dump()

    with open("reference_schemas.json", "w") as ref_file:
        json.dump(ref_schema, ref_file, indent=2)


def get_sqlcol_and_type(
    col_map: dict[str, str],
    field: "FieldSchema",
) -> tuple[str, str]:
    """
    Get sqlcol and sqltype
    """
    fieldtype: ATYPES.ATYPE = ATYPES.ATYPE(field.type)
    sqlcol: str = col_map.get(field.name, clean_name(field.name))
    sqltype: str = TYPEMAP.get(fieldtype, "VARCHAR")

    ## identify richtext as markdown
    if fieldtype == ATYPES.RICH_TEXT:
        # rich text fields are markdown
        sqlcol = f"{sqlcol}_md"

    elif fieldtype == ATYPES.MULTI_RECORD_LINK:
        prefers_single = getattr(
            field.options,
            "prefers_single_record_link",
            getattr(field.options, "prefersSingleRecordLink", False),
        )

        if prefers_single:  # type: ignore
            ## identify single record links as "_id"
            fieldtype = ATYPES.SINGLE_RECORD_LINK
            sqltype: str = TYPEMAP.get(fieldtype, "VARCHAR")
            sqlcol = f"{sqlcol}_id"
        else:
            ## identify multiple record links as "_ids"
            sqlcol = f"{sqlcol}_ids"

    elif fieldtype == ATYPES.MULTI_LOOKUP:
        fieldtype = ATYPES.ATYPE(fieldtype)
        # recurse to get the real type
        # copy the data for the lookup target
        # and apply the current field name
        new_field_data = field.options.result.model_dump()
        new_field_data["name"] = field.name
        new_field_data["id"] = field.id

        new_field = schemas.parse_field_schema(new_field_data)

        sqlcol, sqltype = get_sqlcol_and_type(col_map, new_field)

    return sqlcol, sqltype


def make_sql_schema(
    api_client: "ATApi", tconf: t.Dict[str, t.Any], col_filters: list[str] | None = None
) -> t.Dict:
    """
    Inspect the an Airtable base and table schema and use the configuration to
    build an intermediate structure that can be used to generate she SQL DDL to
    create tables and load data.
    """
    col_filters = col_filters or []

    baseid: t.Any = tconf["base"]
    atable: t.Any = tconf["airtable"]
    tablename: t.Any | None = tconf.get("table", atable.lower())

    bases = api_client.bases(force=True)  # get list of bases with all info

    base = [b for b in bases if b.id == baseid][0]

    table_schema: dict[str, t.Any] = {
        "base": baseid,
        "basename": base.name,
        "airtable": atable,
        "sqltable": tablename,
    }

    # will we use all reflected columns or just the one we
    # map out?
    all_columns: bool = tconf.get("all_columns", True)

    # build defs for SQL table/csv
    ## get schema for table
    col_map: dict[str, str] = tconf.get("columns", {})

    # get Airtable table schema
    # print(api_client.base(base).tables())
    ts = base.table(atable).schema()

    # initialize with id primary key
    # when loading data we will put the recordId here
    coldefs: t.List[dict] = [
        {
            "field": None,
            "type": None,
            "sqlcolumn": "id",
            "sqltype": "varchar",
            "extra": "primary key",
        }
    ]

    field: "FieldSchema"

    for field in ts.fields:
        is_at_pk: bool = field.id == ts.primary_field_id

        # skip condition:
        # - is_valid in options is false
        if getattr(field, "options", None):
            # if no "is_valid" attribute, then it's valid
            is_valid: bool = getattr(field.options, "is_valid", True)
            if not is_valid:
                continue

        # skip conditions:
        # - field is not the Airtable PK (not the same as our PK, the recordId)
        # - AND we aren't reflecting all the columns
        # - AND the field is not in the column map
        skip: bool = (
            not is_at_pk and not all_columns and field.name not in col_map.keys()
        )

        # skip conditions:
        # or if the column matches col_filters
        for pat in col_filters:
            if re.search(pat, field.name):
                skip = True

        if skip:
            continue

        aname: str = field.name
        atype: str = field.type

        sqlcol, sqltype = get_sqlcol_and_type(col_map, field)

        coldef: dict[str, str] = {
            "field": aname,
            "type": atype,
            "sqlcolumn": sqlcol,
            "sqltype": sqltype,
        }

        coldefs.append(coldef)

    table_schema["columns"] = coldefs

    return table_schema


def make_schema_json(
    api_client: "ATApi",
    conf: dict,
    path: Path | str = "schemas.json",
) -> None:
    """
    Inspects the Airtable base schema and, for the tables listed in the config, generates the
    intermediate mappings from Airtable tables to SQL tables.

    Example:
        {
            "base": "appeNGWTuxyPrRBDc",
            "airtable": "CMM Assessments by indicator",
            "sqltable": "assessment_indicator",
            "columns": [
                {
                    "field": "Indicator",
                    "type": "singleRecordLink",
                    "sqlcolumn": "indicator_id",
                    "sqltype": "VARCHAR"
                },
                // ...
            ]
        }

    Special behaviors:

    - Linked Record fields with "allow multiple" selected will be converted to a
      TEXT[] column and `_ids` will be appended to the sql_column name
    - Linked Record fields with "allow multiple" NOT selected will be converted to a
      VARCHAR column and `_id` will be appended to the sql_column name


    See at.ATYPES and at.TYPEMAP for more detail.

    """
    all_schemas: list[dict[str, dict]] = []
    col_filters: list[str] = conf.get("column_filters", [])
    table_confs: list[dict] = conf.get("tables", [])

    for tconf in table_confs:
        tschema: dict[str, dict] = make_sql_schema(api_client, tconf, col_filters)
        all_schemas.append(tschema)

    with open(path, "w") as schema_file:
        json.dump(all_schemas, schema_file, indent=2)


def load_airtable(
    at_client: "ATApi",
    schema: t.Dict[str, t.Any],
) -> t.List[dict[str, t.Any]]:
    """
    Load Airtable data

    at_client: Airtable client
    table_name: name of the table in the airtable Base

    Returns a list of dictionaries with the data from the table
    """
    kwargs: dict[str, t.Any] = {}
    base: str = schema["base"]
    table = schema["airtable"]

    # load table
    table = at_client.table(base, table)

    # get all records
    results = table.all(**kwargs)

    types_map: dict[str, str] = {c["field"]: c["type"] for c in schema["columns"]}
    cols_map: dict[str, str] = {c["field"]: c["sqlcolumn"] for c in schema["columns"]}

    table_data: t.List[dict] = []

    for row in results:
        new_row: dict[str, t.Any] = {}
        for field, sqlcol in cols_map.items():
            if sqlcol == "id":
                new_row["id"] = row["id"]
            else:
                _value: t.Any = row["fields"].get(field, None)
                if types_map[field] == ATYPES.SINGLE_RECORD_LINK:
                    if _value and _value is not None:  # check for empty list
                        _value = _value[0]

                new_row[sqlcol] = _value
        table_data.append(new_row)

    return table_data


def save_table_json(
    data: t.List[dict],
    path: str,
) -> None:
    """
    Save table data to JSON file

    data: list of dictionaries with the data
    f: file object
    """
    import json

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_table_csv(
    data: t.List[dict],
    path: str,
) -> None:
    """
    Save table data to CSV file

    data: list of dictionaries with the data
    f: file object
    """
    import csv

    with open(path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        for row in data:
            writer.writerow(row)
