import os
import typing as t
from pathlib import Path

import click
from dotenv import find_dotenv, load_dotenv
from pyairtable import Api as ATApi

from airtable_db_export import at, db, utils

# find the local env file in the CWD,
# not the library local path
env_file: str = find_dotenv(usecwd=True)
load_dotenv(env_file)


def ensure_path(
    check_path: Path | str,
    must_exist=False,
    parents_only=False,
    base_dir=None,
) -> Path:
    """
    Ensure a path exists by creating it and any parents.

    If must_exist, then fail if the path does not exist yet.
    If parents_only, then only create logical parents of the path (good for paths
        that other processes will actually create)
    """
    path: Path = Path(check_path)

    # fix relative path to accommodate base
    if base_dir and not path.is_absolute():
        # new path in base_dir
        if base_dir.absolute() in path.parents:
            path = base_dir / path.relative_to(base_dir)
        else:
            path = base_dir / path

    # fail if we are enforcing that a path exists
    if must_exist and not path.exists():
        raise (FileNotFoundError(f"Required {path} does not exist!"))

    # create parent
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not parents_only:
        # create path
        if path.is_dir() or path.suffix == "":
            path.mkdir(exist_ok=True)
        else:
            path.touch()

    return path


@click.group()
@click.option(
    "--config-file",
    "-c",
    default="config.yml",
    help="Config file with options and table definitions. See :ref:`config` for more.",
)
@click.option(
    "--no-config-file",
    is_flag=True,
    default=False,
    help="Flag to stop option processing. Only use before create-config command.",
)
@click.option(
    "--base-dir",
    default="",
    help="""
Directory in which to put all generated files. Can be absolute or relative to the
current directory.
""",
)
@click.option(
    "--schemas-file",
    default="",
    help="""
Filename for the intermediate mapping file that maps Airtable tables and fields
to SQL tables and columns.
""",
)
@click.option(
    "--data-dir",
    default="",
    help="""
The directory to download and save Airtable JSON data.
If <base_dir> is set, will be treated as relative to <base_dir> unless it's an absolute path.
""",
)
@click.option(
    "--sql-dir",
    default="",
    help="""
The directory to put generated CREATE DDL files.
If <base_dir> is set, will be treated as relative to <base_dir> unless it's an absolute path.
""",
)
@click.option(
    "--db-file",
    default="",
    help="""
The file path for the generated database.
If <base_dir> is set, will be treated as relative to <base_dir> unless it's an absolute path.
""",
)
@click.pass_context
def cli(
    ctx,
    config_file: Path | str,
    no_config_file: bool,
    base_dir: Path | str,
    schemas_file: str,
    data_dir: str,
    sql_dir: str,
    db_file: str,
):
    """
    Main entry point for the CLI.
    """

    if no_config_file:
        return

    try:
        ensure_path(config_file, must_exist=True)

    except FileNotFoundError:
        click.echo(f"Configuration file {config_file} does not exist!", err=True)
        import sys

        sys.exit(1)

    config: dict = utils.load_config(config_file)

    # if a base_dir was defined, make sure it exists
    if not base_dir:
        base_dir = config.get("base_dir", "")

    if base_dir:
        base_dir = ensure_path(base_dir)

    #################################
    # setup location schemas map file
    if not schemas_file:
        schemas_file = config.get("schemas_file", "schemas.json")

    ####################################
    # setup location for downloaded data
    if not data_dir:
        data_dir = config.get("data_dir", "data")

    ########################################
    # setup location for generated SQL files
    if not sql_dir:
        sql_dir = config.get("sql_dir", "create_sql")

    ######################################
    # setup location for the database file
    # TODO: handle sqlite as well as duckdb formats
    # TODO: handle connection urls for postgres, mysql, etc
    if not db_file:
        db_file = config.get("db_file", "airtable.duckdb")

    ###############################
    # get API key and set up client
    api_key: str | None = os.getenv("AIRTABLE_API_KEY")
    if not api_key:
        raise ValueError("AIRTABLE_API_KEY environment variable is not set.")
    api_client: ATApi = ATApi(api_key)

    #################################
    # create the context for commands
    ctx.obj = {
        "config": config,
        "client": api_client,
        "base_dir": base_dir,
        "schemas_file": schemas_file,
        "data_dir": data_dir,
        "sql_dir": sql_dir,
        "db_file": db_file,
    }


def _generate_schema_map(
    api_client: ATApi,
    config: dict,
    schemas_file: Path | str,
) -> None:
    """
    Generate the intermediate mappings from Airtable tables to SQL tables based
    on the config.
    """
    click.echo(f"Generating schema mappings to file: {schemas_file}")
    at.make_schema_json(api_client, config, schemas_file)


@cli.command(
    "create-config",
    help="Generate a starting config file that you can adapt for your needs.",
)
@click.argument("filename")
def create_config(filename):
    with open(filename, "w") as f:
        f.write("""
# EXAMPLE Airtable DB Export config

# if set, generate all files relative to this directory (created, if it doesn't exist)
base_dir: generated

# name of the intermediate file that maps the actual Airtable schema to your
# configured SQL schema.
# Relative to base_dir.
schemas_file: schemas.json

# where to create downloaded JSON files
# Relative to base_dir.
datadir: data

# where to create the CREATE statement files for your new tables
# Relative to base_dir.
sql_dir: create_sql

# path to the generated database file.
# Relative to base_dir.
db_file: myapp.duckdb

# completely ignore Airtable fields matching these
# regular expressions
column_filters:
- " copy$"

tables:
  # NOTE: any tables that need to be related by ID need to come from the
  # same Airtable base

  # bases need to be identified by ID, found in the Airtable URL starting
  # with "app"
  - base: app123ABC456DEF
    # tables can be identified by name
    airtable: My Table
    # name of the SQL table to create
    table: my_table
    # if true: only export and create the specified columns
    all_columns: false

    # mapping of Airtabe fields to SQL column names
    # used to specify field names, otherwise column names will be
    # "cleaned", removing non-alphanumeric characters and replacing
    # spaces with underscores (_)
    columns:
      # links
      "Name": name
""")


@cli.command(
    "generate-schema-map",
    help="""Generate schemas.json file. This file is intermediary and contains
the information needed to map the selected Airtable fields to SQL tables and columns
""",
)
@click.pass_context
def generate_schema_map(ctx):
    config = ctx.obj["config"]

    base_dir = ctx.obj["base_dir"]
    schemas_file = ctx.obj["schemas_file"]
    schemas_file = ensure_path(schemas_file, base_dir=base_dir)

    api_client = ctx.obj["client"]
    _generate_schema_map(api_client, config, schemas_file)


def _download_data(
    api_client: ATApi,
    schemas_file: Path | str,
    data_dir: Path | str,
    save_func: t.Callable,
) -> None:
    """
    Download data from the tables in Airtable defined in <schemas_file> and save
    in <date_dir> using <save_func>.
    """

    schemas: list[dict[str, t.Any]] = utils.load_schemas(schemas_file)
    for schema in schemas:
        click.echo(
            f"Loading data from Base: {schema['base']} Table: {schema['airtable']}..."
        )
        data: list[dict[str, t.Any]] = at.load_airtable(api_client, schema)
        click.echo(f"Saving data to {schema['sqltable']}...")
        save_func(data, f"{data_dir}/{schema['sqltable']}")


@cli.command(
    "download-data",
    help="""
Download Airtable data. Files will be stored in <data_dir>.
""",
)
@click.option(
    "-f",
    "--format",
    "formats",
    type=click.Choice(["json", "csv"]),
    default=["json"],
    multiple=True,
    help="Formats to export downloaded data as.",
)
@click.pass_context
def download_data(ctx, formats: list):
    """
    Download data from Airtable and save as JSON or CSV
    for archive or import into another tool.
    """
    api_client = ctx.obj["client"]

    base_dir = ctx.obj["base_dir"]

    schemas_file = ctx.obj["schemas_file"]

    fmt_funcmap: dict = {
        "json": utils.save_table_json,
        "csv": utils.save_table_csv,
    }

    # fail if schema mapping file has not been created
    schemas_file = ensure_path(schemas_file, base_dir=base_dir, must_exist=True)

    data_dir = ctx.obj["data_dir"]
    data_dir = ensure_path(data_dir, base_dir=base_dir)

    click.echo("Downloading data from Airtable...")
    for fmt in formats:
        save_func = fmt_funcmap[fmt]
        _download_data(api_client, schemas_file, data_dir, save_func)
    click.echo("Downloading data complete")


def _create_sql(schemas_file: Path | str, sql_dir: Path | str) -> None:
    click.echo("Generate CREATE DDL")

    schemas: list[dict[str, t.Any]] = utils.load_schemas(schemas_file)
    db.make_create_files(schemas, sql_dir)
    click.echo("CREATE DDL complete")


@cli.command(
    "create-sql",
    help="""
    Generate CREATE DDL for database tables based on Airtable schema and table
    configuration in the config.yml.
""",
)
@click.pass_context
def create_sql(ctx):
    """ """
    base_dir = ctx.obj["base_dir"]

    schemas_file = ctx.obj["schemas_file"]
    schemas_file = ensure_path(schemas_file, base_dir=base_dir, must_exist=True)

    sql_dir = ctx.obj["sql_dir"]
    sql_dir = ensure_path(sql_dir, base_dir=base_dir)

    _create_sql(schemas_file, sql_dir)


def _create_db(
    schemas_file: Path | str,
    db_file: Path | str,
    sql_dir: Path | str,
) -> None:
    """ """
    click.echo(f"Create database in {db_file}")

    schemas = utils.load_schemas(schemas_file)
    db.bootstrap_db(db_file, schemas, sql_dir)


@cli.command(
    "create-db",
    help="""
Create database from generated DDL.
""",
)
@click.pass_context
def create_db(ctx):
    """ """
    base_dir = ctx.obj["base_dir"]

    schemas_file = ctx.obj["schemas_file"]
    schemas_file = ensure_path(schemas_file, base_dir=base_dir, must_exist=True)

    sql_dir = ctx.obj["sql_dir"]
    sql_dir = ensure_path(sql_dir, base_dir=base_dir, must_exist=True)

    db_file = ctx.obj["db_file"]
    db_file = ensure_path(db_file, parents_only=True, base_dir=base_dir)

    _create_db(schemas_file, db_file, sql_dir)


def _load_db(db_file: Path | str, schemas_file: Path | str, data_dir: Path | str):
    """ """
    schemas = utils.load_schemas(schemas_file)
    # load create tables
    click.echo("Load database")
    db.load_db(db_file, schemas, data_dir)


@cli.command(
    "load-db",
    help="""
Load JSON data from Airtable into the database.
""",
)
@click.pass_context
def load_db(ctx):
    """ """
    base_dir = ctx.obj["base_dir"]

    schemas_file = ctx.obj["schemas_file"]
    schemas_file = ensure_path(schemas_file, base_dir=base_dir, must_exist=True)

    data_dir = ctx.obj["data_dir"]
    data_dir = ensure_path(data_dir, base_dir=base_dir, must_exist=True)

    db_file = ctx.obj["db_file"]
    db_file = ensure_path(
        db_file, parents_only=True, base_dir=base_dir, must_exist=True
    )

    _load_db(db_file, schemas_file, data_dir)


@cli.command()
@click.pass_context
def all(ctx):
    """ """
    config = ctx.obj["config"]

    db_file = ctx.obj["db_file"]
    if not db_file:
        raise (Exception("DBFILE not provided"))

    base_dir = ctx.obj["base_dir"]
    schemas_file = ctx.obj["schemas_file"]
    data_dir = ctx.obj["data_dir"]
    sql_dir = ctx.obj["sql_dir"]
    api_client = ctx.obj["client"]
    db_file = ctx.obj["db_file"]

    schemas_file = ensure_path(schemas_file, base_dir=base_dir)
    data_dir = ensure_path(data_dir, base_dir=base_dir)
    sql_dir = ensure_path(sql_dir, base_dir=base_dir)
    db_file = ensure_path(db_file, parents_only=True, base_dir=base_dir)

    # update airtable schema
    _generate_schema_map(api_client, config, schemas_file)
    # generate sql schemas
    _create_sql(schemas_file, sql_dir)
    # fetch airtable data
    _download_data(api_client, schemas_file, data_dir, utils.save_table_json)
    # build db
    _create_db(schemas_file, db_file, sql_dir)
    # load db
    _load_db(db_file, schemas_file, data_dir)


if __name__ == "__main__":
    cli()
