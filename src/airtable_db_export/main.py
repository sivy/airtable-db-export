import os
import typing as t
from pathlib import Path

import click
from dotenv import load_dotenv
from pyairtable import Api as ATApi

from airtable_db_export import at, db, utils

load_dotenv()


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
@click.option("--config-file", "-c", default="config.yml")
@click.option("--base-dir", default="")
@click.option("--schemas-file", default="")
@click.option("--data-dir", default="")
@click.option("--sql-dir", default="")
@click.option("--db-file", default="")
@click.pass_context
def cli(
    ctx,
    config_file: Path | str,
    base_dir: Path | str,
    schemas_file: str,
    data_dir: str,
    sql_dir: str,
    db_file: str,
):
    """
    Main entry point for the CLI.
    """
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


def _generate_schema_map(api_client: ATApi, config: dict, schemas_file: Path | str) -> None:
    """
    Generate the intermediate mappings from Airtable tables to SQL tables based
    on the config.
    """
    click.echo(f"Generating schema mappings to file: {schemas_file}")
    at.make_schema_json(api_client, config, schemas_file)


@cli.command(
    "generate-schema-map",
    help="Generate schemas.json file",
)
@click.pass_context
def generate_schema_map(ctx):
    config = ctx.obj["config"]

    base_dir = ctx.obj["base_dir"]
    schemas_file = ctx.obj["schemas_file"]
    schemas_file = ensure_path(schemas_file, base_dir=base_dir)

    api_client = ctx.obj["client"]
    _generate_schema_map(api_client, config, schemas_file)


def _download_data_json(api_client: ATApi, schemas_file: Path | str, data_dir: Path | str) -> None:
    """
    Load data from tables in Airtable to JSON in DATADIR.
    """
    click.echo("Downloading data from Airtable...")

    schemas: list[dict[str, t.Any]] = utils.load_schemas(schemas_file)
    for schema in schemas:
        click.echo(f"Loading data from Base: {schema['base']} Table: {schema['airtable']}...")
        data: list[dict[str, t.Any]] = at.load_airtable(api_client, schema)
        click.echo(f"Saving data to {schema['sqltable']}.json...")
        at.save_table_json(data, f"{data_dir}/{schema['sqltable']}.json")

    click.echo("Downloading data complete")


@cli.command("download-json")
@click.pass_context
def download_data_json(ctx):
    """ """
    api_client = ctx.obj["client"]

    base_dir = ctx.obj["base_dir"]

    schemas_file = ctx.obj["schemas_file"]
    # fail if schema mapping file has not been created
    schemas_file = ensure_path(schemas_file, base_dir=base_dir, must_exist=True)

    data_dir = ctx.obj["data_dir"]
    data_dir = ensure_path(data_dir, base_dir=base_dir)

    _download_data_json(api_client, schemas_file, data_dir)


def _create_sql(schemas_file: Path | str, sql_dir: Path | str) -> None:
    click.echo("Generate CREATE DDL")

    schemas: list[dict[str, t.Any]] = utils.load_schemas(schemas_file)
    db.make_create_files(schemas, sql_dir)
    click.echo("CREATE DDL complete")


@cli.command("create-sql", help="Generate database definitions")
@click.pass_context
def create_sql(ctx):
    """ """
    base_dir = ctx.obj["base_dir"]

    schemas_file = ctx.obj["schemas_file"]
    schemas_file = ensure_path(schemas_file, base_dir=base_dir, must_exist=True)

    sql_dir = ctx.obj["sql_dir"]
    sql_dir = ensure_path(sql_dir, base_dir=base_dir)

    _create_sql(schemas_file, sql_dir)


def _create_db(schemas_file: Path | str, db_file: Path | str, sql_dir: Path | str) -> None:
    """ """
    click.echo(f"Create database in {db_file}")

    schemas = utils.load_schemas(schemas_file)
    db.bootstrap_db(db_file, schemas, sql_dir)


@cli.command("create-db", help="Generate database definitions")
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
    print(f"db_file: {db_file.absolute()}")

    _create_db(schemas_file, db_file, sql_dir)


def _load_db(db_file: Path | str, schemas_file: Path | str, data_dir: Path | str):
    """ """
    schemas = utils.load_schemas(schemas_file)
    # load create tables
    click.echo("Load database")
    db.load_db(db_file, schemas, data_dir)


@cli.command("load-db")
@click.pass_context
def load_db(ctx):
    """ """
    base_dir = ctx.obj["base_dir"]

    schemas_file = ctx.obj["schemas_file"]
    schemas_file = ensure_path(schemas_file, base_dir=base_dir, must_exist=True)

    data_dir = ctx.obj["data_dir"]
    data_dir = ensure_path(data_dir, base_dir=base_dir, must_exist=True)

    db_file = ctx.obj["db_file"]
    db_file = ensure_path(db_file, parents_only=True, base_dir=base_dir, must_exist=True)

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
    _download_data_json(api_client, schemas_file, data_dir)
    # build db
    _create_db(schemas_file, db_file, sql_dir)
    # load db
    _load_db(db_file, schemas_file, data_dir)


if __name__ == "__main__":
    cli()
