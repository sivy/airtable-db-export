.. _example:

End to End Example
==================

Sample App
----------

The best way to show what Airtable DB Export does is to show it. Let's imagine an astonishingly simple Airtable app for managing properties and residents:

A Contacts table with some basic fields about people:

.. image:: img/adbe_example_contacts.png
   :alt: Screenshot of the Contacts table in Airtable

A Properties table with an address and a link to Contacts as "Residents"

.. image:: img/adbe_example_properties.png
   :alt: Screenshot of the Properties table in Airtable

We created this app a while back so that our employees could easily manage properties and tenants. Now we want to create a small database app that our new Business Development manager can use with their BI tools, but we don't yet want to replace the whole app that the employees are used to.


Setup
-----

First your going to need an Airtable API token, which you can create at the `Airtable Buider Hub <https://airtable.com/create/tokens>`__. Write it down or save it somewhere for later.

Since this is a Python library, we're going to assume you have a Python project with an environment already set up. If not, see `Installation <install.html>`__.::

    $ pip install airtable-db-export
    $ adbe --no-config-file create-config adbe-config.yml

This installs Airtable DB Export and starts a local configuration file for your app. Open up ``abde-config.yml`` (the name is not itself important) in an editor and let's see what the
command created.::

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
    - base: appRandomStringBaseID
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
