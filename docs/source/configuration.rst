.. _config:

Configuration
=============

The ADBE (ADBE) configuration file contains:

- Options that determine where generated files are created. These can be overridden in the :ref:`cli` options.
- Table and column defitions and configuration that controls which tables and fields are downloaded, and how they are translated to SQL tables and columns in the resulting data model.

The following config can be created with ``abde --no-config-file create-config config.yml``.

Configuration by Section
------------------------

``base_dir``
~~~~~~~~~~~~

::

    # ADBE config

    # if set, generate all files relative to this directory (created, if it doesn't exist)
    base_dir: generated

``base_dir``: defaults to "generated" in the generated example config file. This can be left out, or set on the CLI with ``--base-dir <path>``.

``schemas_file``
~~~~~~~~~~~~~~~~

::

    # name of the intermediate file that maps the actual Airtable schema to your
    # configured SQL schema.
    # Relative to base_dir.
    schemas_file: schemas.json

``schemas_file``: defaults to "schemas.json" in the generated example config file. This can be left out, or set on the CLI with ``--schemas-file <path>``.

``data_dir``
~~~~~~~~~~~~~~~~

::

    # where to create downloaded JSON files
    # Relative to base_dir.
    data_dir: data

``data_dir``: defaults to "data" in the generated example config file. This can be left out (will put files in ``base_dir`` or ``.``, or set on the CLI with ``--data-dir <path>``.

``sql_dir``
~~~~~~~~~~~

::

    # where to create the CREATE statement files for your new tables
    # Relative to base_dir.
    sql_dir: create_sql

``sql_dir``: defaults to "create_sql" in the generated example config file. This can be left out (will put ``create_<table>.sql`` files in ``base_dir`` or ``.``), or set on the CLI with ``--sql-dir <path>``.

``db_file``
~~~~~~~~~~~

::

    # path to the generated database file.
    # Relative to base_dir.
    db_file: myapp.duckdb

``db_file`` defaults to "myapp.duckdb" in the generated example config file. This can be left out but if it is not in the config file then ``--db-file <path>`` MUST be specified on the CLI.

``column_filters``
~~~~~~~~~~~~~~~~~~

By default, ADBE will inspect the schema of your Airtable base, find the tables you have added in the config file, and convert all fields in the schema to columns in the resulting database. However, due to Airtable's usefulness as a low-code solution, there may often be extra fields in your tables left over from changes to the Airtable app made by different users over time. If youa are seeing extra fields being exported, you can filter out columns by regex, like:::

    # completely ignore Airtable fields matching these
    # regular expressions
    column_filters:
    - " copy$"
    - "\(old\)"

``tables``
~~~~~~~~~~

The core configuration for ADBE. This is where you determine which tables you want exported from Airtable and how you want them to be represented in the SQL database.::

    tables:
    # NOTE: any tables that need to be related by ID need to come from the
    # same Airtable base

    # bases need to be identified by ID, found in the Airtable URL starting
    # with "app"


Currently due to the way that we get table data, the base for a table must be specified by ID, which can only be found in the URL of the base in Airtable, starting with "app": ``https://airtable.com/app123ABC456DEF/``::

    - base: app123ABC456DEF

Tables however can be identified by the table name:::

      # tables can be identified by name
      airtable: My Table

Provide a name for the SQL table in the resulting database:::

      # name of the SQL table to create
      table: my_table

If you want to export `only` the specified columns, ignoring all others, set ``all_columns`` to ``false``.::

      # if true: only export and create the specified columns
      all_columns: false

Column mapping: ``columns`` is a mapping from Airtable field names to sql column names. If a field is not listed here and ``all_columns`` is not ``false``, the general cleaning rules will apply (non-alpha characters are removed, spaces are replced with underscores [``_``]).::

      # mapping of Airtable fields to SQL column names
      # used to specify field names, otherwise column names will be
      # "cleaned", removing non-alphanumeric characters and replacing
      # spaces with underscores (_)
      columns:
         "Name": name

Mapping Linked Records fields
-----------------------------

There is one special case exception to this mapping pattern, Airtable "Linked Records" fields. ADBE converts Linked Record fields so as to try and preserve the ability to properly join on these columns when querying the new database.

- If the Linked Records field has "Allow linking to multiple records" set, it will be converted to a ``VARCHAR[]`` (native array column)
    - The sql column name will be the name set in ``tables:``, but will be appended with ``_ids``.
    - The content will be the Airtable recordIds for the linked records. These recordIds are only valid between tables in the same Base.
- If the Linked Records fields does `NOT` have "Allow linking to multiple records" set, it will be converted to a ``VARCHAR`` field (not a list)
    - The SQL column name will be the name set in ``tables:``, but will be appended with ``_id``.
    - The content will be the Airtable recordId for the linked record.
