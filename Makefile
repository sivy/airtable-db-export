.PHONY: generate-schemas download-json create-sql create-db load-db all clean test

export PATH := src:$(PATH)

DBFILE := "airtable.duckdb"
CREATE_SQL_DIR := "create_sql"
###
# Setup tasks

.env:
	@echo "AIRTABLE_API_KEY=your_api_key_here" > .env
	@echo ".env file created. Please edit it to add your actual Airtable API key."

create-env: .env

### Data tasks
# Generate schema JSON files for all tables
schemas.json:
	uv run python src/main.py generate-schemas

generate-schemas: schemas.json

# Download Airtable data as JSON for each table
data/%.json: schemas.json
	uv run python src/main.py download-json

download-json: data/%.json

$(CREATE_SQL_DIR):
	mkdir -a $(CREATE_SQL_DIR)

# Generate SQL CREATE TABLE statements for all tables
$(CREATE_SQL_DIR)/%.sql: $(CREATE_SQL_DIR) schemas.json
	uv run python src/main.py create-sql

create-sql: $(CREATE_SQL_DIR)/create_%.sql

# Create the SQLite database file (default: wmis.duckdb)
$(DBFILE): $(CREATE_SQL_DIR)/create_%.sql
	uv run python src/main.py create-db --dbfile $(DBFILE)

create-db: $(DBFILE)

# Load data into the SQLite database
load-db: $(DBFILE) data/%.json
	uv run python src/main.py load-db --dbfile $(DBFILE)

# Run all steps in sequence
all:
	uv run python src/main.py all --dbfile $(DBFILE)

# Run tests
test:
	uv run pytest tests/ -v

clean-db:
	rm -f $(DBFILE)

# Clean generated files
# except .env which might contain sensitive and temporary information
clean:
	rm -rf data/*.json $(CREATE_SQL_DIR)/create_*.sql $(DBFILE) schemas.json

server:
	uv run python src/dash.py
