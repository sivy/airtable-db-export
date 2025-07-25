# Airtable DB Export (ADBE)

Export Airtable tables to a SQL database.

## Background

[Airtable](https://airtable.com/) is a low-code platform that allows individuals, teams, and
businesses to build database-backed applications. As a low-code tool Airtable is optimized for
non-technical users to be able to create new tables, forms and interfaces quickly.

An individual or organization using Airtable may find that after building a quick solution
or prototype in Airtable, they want to export this data into a structure that is optimized
for use in tranditional developement or for further analysis.

[Airtable DB Export](https://github.com/sivy/airtable-db-export) enables developers to download
tables of data from Airtable as JSON files, configure the mapping of Airtable tables and fields
to SQL tables and columns, and (currently) create and load a DuckDB SQL database with downloaded
data.



## Documentation

Read more on [ReadTheDocs](https://airtable-db-export.readthedocs.io/en/latest/).

### Using pip

`pip install airtable-db-export`

### Using uv

`uv add airtable-db-export`

## Usage

```
Usage: adbe [OPTIONS] COMMAND [ARGS]...

  Main entry point for the CLI.

Options:
  -c, --config TEXT
  --base-dir TEXT
  --schemas-file TEXT
  --data-dir TEXT
  --sql-dir TEXT
  --db-file TEXT
  --help               Show this message and exit.

Commands:
  all
  create-db            Generate database definitions
  create-sql           Generate database definitions
  download-json
  generate-schema-map
  load-db
```

## Configuration

## Similar  projects

- Simon WIllison's [Airtable Export](https://github.com/simonw/airtable-export)