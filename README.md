# Airtable DB Export (ADBE)

Export Airtable tables to a SQL database.

## Background

## Install



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

## Similar  projects

- Simon WIllison's [Airtable Export](https://github.com/simonw/airtable-export), but only exports to SQLite, with little support for customizing the database structure.