"""Tests for backend detection and adapter selection."""

import pytest
from pathlib import Path

from airtable_db_export import backends


class TestBackendDetection:
    """Test backend auto-detection from file extension."""

    def test_detect_duckdb_extension(self):
        """Should detect .duckdb extension."""
        assert backends.detect_backend("test.duckdb") == "duckdb"
        assert backends.detect_backend("/path/to/db.duckdb") == "duckdb"

    def test_detect_sqlite_extension(self):
        """Should detect .sqlite extension."""
        assert backends.detect_backend("test.sqlite") == "sqlite"
        assert backends.detect_backend("/path/to/db.sqlite") == "sqlite"

    def test_detect_ambiguous_db_raises_error(self):
        """Should raise error for ambiguous .db extension."""
        with pytest.raises(ValueError, match="Ambiguous database extension"):
            backends.detect_backend("test.db")

    def test_detect_ambiguous_db3_raises_error(self):
        """Should raise error for ambiguous .db3 extension."""
        with pytest.raises(ValueError, match="Ambiguous database extension"):
            backends.detect_backend("test.db3")

    def test_detect_ambiguous_sqlite3_raises_error(self):
        """Should raise error for ambiguous .sqlite3 extension."""
        with pytest.raises(ValueError, match="Ambiguous database extension"):
            backends.detect_backend("test.sqlite3")

    def test_detect_unknown_extension_defaults_to_duckdb(self):
        """Should default to duckdb for unknown extensions."""
        assert backends.detect_backend("test.mydb") == "duckdb"
        assert backends.detect_backend("test.data") == "duckdb"

    def test_detect_no_extension_defaults_to_duckdb(self):
        """Should default to duckdb when no extension."""
        assert backends.detect_backend("testdb") == "duckdb"

    def test_detect_with_path_object(self):
        """Should work with Path objects."""
        assert backends.detect_backend(Path("test.duckdb")) == "duckdb"
        assert backends.detect_backend(Path("test.sqlite")) == "sqlite"


class TestBackendValidation:
    """Test backend validation."""

    def test_validate_duckdb(self):
        """Should accept 'duckdb'."""
        assert backends.validate_backend("duckdb") == "duckdb"
        assert backends.validate_backend("DUCKDB") == "duckdb"
        assert backends.validate_backend("DuckDB") == "duckdb"

    def test_validate_sqlite(self):
        """Should accept 'sqlite'."""
        assert backends.validate_backend("sqlite") == "sqlite"
        assert backends.validate_backend("SQLITE") == "sqlite"
        assert backends.validate_backend("SQLite") == "sqlite"

    def test_validate_invalid_backend(self):
        """Should reject unsupported backends."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            backends.validate_backend("postgresql")
        with pytest.raises(ValueError, match="Unsupported backend"):
            backends.validate_backend("mysql")
        with pytest.raises(ValueError, match="Unsupported backend"):
            backends.validate_backend("invalid")


class TestTypeMapping:
    """Test type mappings per backend."""

    def test_get_typemap_duckdb(self):
        """Should return DuckDB type map."""
        typemap = backends.get_typemap("duckdb")
        assert typemap == backends.TYPEMAP_DUCKDB
        assert typemap["checkbox"] == "BOOLEAN"
        assert typemap["multipleSelects"] == "TEXT[]"

    def test_get_typemap_sqlite(self):
        """Should return SQLite type map."""
        typemap = backends.get_typemap("sqlite")
        assert typemap == backends.TYPEMAP_SQLITE
        assert typemap["checkbox"] == "INTEGER"  # SQLite: 0 or 1
        assert typemap["multipleSelects"] == "TEXT"  # SQLite: JSON string

    def test_get_typemap_invalid_backend(self):
        """Should raise error for invalid backend."""
        with pytest.raises(ValueError):
            backends.get_typemap("invalid")

    def test_sql_type_for_airtable_duckdb(self):
        """Should return correct SQL type for Airtable field in DuckDB."""
        assert backends.sql_type_for_airtable("checkbox", "duckdb") == "BOOLEAN"
        assert backends.sql_type_for_airtable("singleLineText", "duckdb") == "VARCHAR"
        assert backends.sql_type_for_airtable("multipleSelects", "duckdb") == "TEXT[]"

    def test_sql_type_for_airtable_sqlite(self):
        """Should return correct SQL type for Airtable field in SQLite."""
        assert backends.sql_type_for_airtable("checkbox", "sqlite") == "INTEGER"
        assert backends.sql_type_for_airtable("singleLineText", "sqlite") == "TEXT"
        assert backends.sql_type_for_airtable("multipleSelects", "sqlite") == "TEXT"

    def test_sql_type_for_airtable_unknown_field_type(self):
        """Should return TEXT for unknown Airtable field type."""
        assert backends.sql_type_for_airtable("unknownType", "duckdb") == "TEXT"
        assert backends.sql_type_for_airtable("unknownType", "sqlite") == "TEXT"


class TestAdapterSelection:
    """Test adapter factory."""

    def test_get_adapter_duckdb(self):
        """Should return DuckDB adapter."""
        adapter = backends.get_adapter("duckdb")
        assert isinstance(adapter, backends.DuckDBAdapter)

    def test_get_adapter_sqlite(self):
        """Should return SQLite adapter."""
        adapter = backends.get_adapter("sqlite")
        assert isinstance(adapter, backends.SQLiteAdapter)

    def test_get_adapter_case_insensitive(self):
        """Should be case-insensitive."""
        adapter1 = backends.get_adapter("DUCKDB")
        assert isinstance(adapter1, backends.DuckDBAdapter)

        adapter2 = backends.get_adapter("SQLITE")
        assert isinstance(adapter2, backends.SQLiteAdapter)

    def test_get_adapter_invalid_backend(self):
        """Should raise error for invalid backend."""
        with pytest.raises(ValueError):
            backends.get_adapter("invalid")


class TestDuckDBAdapter:
    """Test DuckDB adapter."""

    def test_adapter_instance(self):
        """Should create adapter instance."""
        adapter = backends.DuckDBAdapter()
        assert adapter is not None

    def test_adapter_methods_exist(self):
        """Should have required methods."""
        adapter = backends.DuckDBAdapter()
        assert hasattr(adapter, "connect")
        assert hasattr(adapter, "close")
        assert hasattr(adapter, "execute_sql")
        assert hasattr(adapter, "execute_insert_from_json")


class TestSQLiteAdapter:
    """Test SQLite adapter."""

    def test_adapter_instance(self):
        """Should create adapter instance."""
        adapter = backends.SQLiteAdapter()
        assert adapter is not None

    def test_adapter_methods_exist(self):
        """Should have required methods."""
        adapter = backends.SQLiteAdapter()
        assert hasattr(adapter, "connect")
        assert hasattr(adapter, "close")
        assert hasattr(adapter, "execute_sql")
        assert hasattr(adapter, "execute_insert_from_json")


class TestBackendConstants:
    """Test backend constants."""

    def test_backends_list(self):
        """Should have supported backends list."""
        assert "duckdb" in backends.BACKENDS
        assert "sqlite" in backends.BACKENDS

    def test_typemaps_exist(self):
        """Should have type maps for both backends."""
        assert backends.TYPEMAP_DUCKDB is not None
        assert backends.TYPEMAP_SQLITE is not None

    def test_typemaps_different(self):
        """Type maps should have differences for key types."""
        # BOOLEAN differs
        assert (
            backends.TYPEMAP_DUCKDB["checkbox"] != backends.TYPEMAP_SQLITE["checkbox"]
        )
        # Arrays differ
        assert (
            backends.TYPEMAP_DUCKDB["multipleSelects"]
            != backends.TYPEMAP_SQLITE["multipleSelects"]
        )

    def test_typemaps_have_common_types(self):
        """Both type maps should have common Airtable types."""
        common_types = ["singleLineText", "number", "currency"]
        for atype in common_types:
            assert atype in backends.TYPEMAP_DUCKDB
            assert atype in backends.TYPEMAP_SQLITE
