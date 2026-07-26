-include .env
export

POSTGRES_PORT ?= 55432
PYTHON := backend/.venv/bin/python
ALEMBIC := backend/.venv/bin/alembic -c backend/alembic.ini

.PHONY: db-up db-down db-status db-create db-reset migrate migrate-down
.PHONY: test-postgres load-fixtures validate-fixtures inspect-schema
.PHONY: require-database-url require-test-database-url

require-database-url:
	@test -n "$(DATABASE_URL)" || \
		(echo "DATABASE_URL es obligatoria. Copie .env.example a .env." >&2; exit 1)

require-test-database-url:
	@test -n "$(TEST_DATABASE_URL)" || \
		(echo "TEST_DATABASE_URL es obligatoria para integración." >&2; exit 1)

db-up:
	POSTGRES_PORT=$(POSTGRES_PORT) scripts/postgres_local.sh up

db-down:
	POSTGRES_PORT=$(POSTGRES_PORT) scripts/postgres_local.sh down

db-status:
	POSTGRES_PORT=$(POSTGRES_PORT) scripts/postgres_local.sh status

db-create:
	POSTGRES_PORT=$(POSTGRES_PORT) scripts/postgres_local.sh create

db-reset:
	POSTGRES_PORT=$(POSTGRES_PORT) scripts/postgres_local.sh reset

migrate: require-database-url
	DATABASE_URL='$(DATABASE_URL)' $(ALEMBIC) upgrade head

migrate-down: require-database-url
	DATABASE_URL='$(DATABASE_URL)' $(ALEMBIC) downgrade base

test-postgres: require-database-url require-test-database-url
	DATABASE_URL='$(TEST_DATABASE_URL)' $(ALEMBIC) upgrade head
	TEST_DATABASE_URL='$(TEST_DATABASE_URL)' DATABASE_URL='$(DATABASE_URL)' \
		$(PYTHON) -m pytest -c backend/pyproject.toml -m postgres backend/tests

load-fixtures: require-database-url
	DATABASE_URL='$(DATABASE_URL)' $(PYTHON) scripts/load_fictitious_evidence.py

validate-fixtures: require-database-url
	DATABASE_URL='$(DATABASE_URL)' $(PYTHON) scripts/validate_fictitious_dossier.py

inspect-schema: require-database-url
	DATABASE_URL='$(DATABASE_URL)' $(PYTHON) scripts/inspect_postgres_schema.py
