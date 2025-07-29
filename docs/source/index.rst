.. Airtable DB Export documentation master file, created by
   sphinx-quickstart on Thu Jul 24 05:50:38 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Airtable DB Export documentation
================================

`Airtable`_ is a low-code platform that allows individuals, teams, and businesses to
build database-backed applications. As a low-code tool Airtable is optimized for
non-technical users to be able to create new tables, forms and interfaces quickly.

.. _Airtable: https://airtable.com/

An individual or organization using Airtable may find that after building a quick solution
or prototype in Airtable, they want to export this data into a structure that is optimized
for use in traditional development or for further analysis.

`Airtable DB Export`_ enables developers to download tables of data from Airtable as JSON files,
configure the mapping of Airtable tables and fields to SQL tables and columns, and (currently)
create and load a DuckDB SQL database with downloaded data.

.. _Airtable DB Export: https://github.com/sivy/airtable-db-export

Currently ``airtable-db-export`` creates a `DuckDB`_-native database, due to DuckDB's small footprint, embedability, and broad support for standard SQL. Support for other database backends, like SQLite and PostgreSQL (through DuckDB's support) is planned.

.. _DuckDB: https://duckdb.org/

Workflow
--------

The general workflow tasks when using ADBE:

- :ref:`workflow_airtable_setup`
- :ref:`workflow_config`
- :ref:`workflow_schemas`
- :ref:`workflow_create_sql`
- :ref:`workflow_create_db`
- :ref:`workflow_download`
- :ref:`workflow_load_db`

One thing to note: most of these tasks can be used independently depending on your needs. For example, actually generating the create DDL won't be needed if your configuration and source tables have not changed – you can just download the json data and load it.

.. _workflow_airtable_setup:

Airtable API Setup
~~~~~~~~~~~~~~~~~~

First you will need an Airtable API token, which you can create at the `Airtable Buider Hub <https://airtable.com/create/tokens>`__.
Write it down or save it somewhere. Airtable DB Export will look for API token in your environment. The easiest way to use it in local development is to create a ``.env`` file in your repo (make sure it's ignored by your source control) and add the token like:::

   AIRTABLE_API_KEY="<api token>"


.. _workflow_config:

Configuration
~~~~~~~~~~~~~
Configure which tables you want to export, and how to set up different field -> column mappings.
See the section on :ref:`config` for more.

.. _workflow_schemas:

Generate Schema Map
~~~~~~~~~~~~~~~~~~~

Airtable DB Export will look for your API token in your environment, and will connect to Airtable to inspect the configured tables. Then it will create a mapping file between Airtable tables and fields to
SQL tables and columns based on your configuration. By default `adbe` will read all fields in the target table, add the cleaned airtable name as the SQL table, and cleaned field names as columns. Configuring ``column_filters`` and ``tables:columns`` allows more control over which fields are exported and how they are named in the ``schemas.json`` and subsequent SQL database.

.. code-block:: bash

   $ adbe -c config.yml generate-schema-map

Override the ``--schemas-file`` location:

.. code-block:: bash

   $ adbe -c config.yml --schemas-file schemas-map.json generate-schema-map

.. _workflow_create_sql:

Create Database DDL SQL
~~~~~~~~~~~~~~~~~~~~~~~

Once the ``schemas.json`` (the default name, but whatever you set `schemas_file` to in the config file or passed in ``--schemas-file`` on the command line) is created, ADBE can be used with ``create-sql`` to generate the SQL DDL that will create the data model in the new database.

.. code-block:: bash

   $ adbe -c config.yml create-sql
   

Overriding the ``--sql-dir``:

.. code-block:: bash

   $ adbe -c config.yml --sql-dir sql create-sql

.. _workflow_create_db:

Create Database
~~~~~~~~~~~~~~~

After generating the SQL DDL to create the database tables, you can actually create the database.

.. code-block:: bash

   $ adbe -c config.yml create-db

To override the database file path in the config (or if you did not set one) pass ``--db-file`` with the path:

.. code-block:: bash

   $ adbe -c config.yml --db-file example.duckdb create-db

This can be useful for testing, for example.

.. _workflow_download:

Download Airtable Data
++++++++++++++++++++++

To download all the data in your configured tables, use the `download-json` command:

.. code-block:: bash

   $ adbe -c config.yml download-json

Again, to override the configured destination, pass ``--data-dir`` on the command line:

.. code-block:: bash

   $ adbe -c config.yml --data-dir tmp_data download-json

.. _workflow_load_db:

Load Database
++++++++++++++++++++++

Finally, to load all downloaded data:

.. code-block:: bash

   $ adbe -c config.yml load-db


End to End Example
------------------

Let's look at an `Example <example.html>`__.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   install
   configuration
   cli
   example
   license
