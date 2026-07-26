# Faro Político

Plataforma histórica de evidencia pública para construir dossiers verificables.
Conserva hechos, documentos, versiones, revisiones y rectificaciones sin
formular acusaciones propias.

## Requisitos

- Python 3.12 o superior;
- PostgreSQL 17 o superior;
- herramientas PostgreSQL: `postgres`, `initdb`, `pg_ctl`, `psql`, `createdb`;
- Make;
- Docker es opcional y no se requiere para la modalidad local elegida.

En Arch Linux:

```bash
sudo pacman -S postgresql
```

El entorno de validación no permitía `sudo`, por lo que se extrajo el paquete
oficial PostgreSQL 18.4 bajo `.local/postgresql/`. `postgres_local.sh` detecta
esa ubicación o una instalación normal disponible en `PATH`.

## Instalación Python

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cd ..
cp .env.example .env
```

`DATABASE_URL` es obligatoria. No existe fallback ni credencial incorporada en
el código. Para la instancia local aislada:

```dotenv
DATABASE_URL=postgresql+psycopg://faro_politico_app@127.0.0.1:55432/faro_politico_dev
TEST_DATABASE_URL=postgresql+psycopg://faro_politico_app@127.0.0.1:55432/faro_politico_test
```

La configuración local escucha solo en loopback. Para otros entornos, guarda la
contraseña fuera de Git y agrégala a la URL mediante variables locales.

## PostgreSQL local

La modalidad elegida es un clúster administrado por el usuario con `pg_ctl`.
Los datos quedan en `.postgres-data/`, fuera de Git. Se crean:

- rol `faro_politico_app`, sin privilegios de superusuario, creación de roles o
  creación de bases;
- base de desarrollo `faro_politico_dev`;
- base aislada de tests `faro_politico_test`;
- puerto local `55432`.

Comandos:

```bash
make db-up
make db-status
make db-create
make db-down
```

`make db-reset` exige escribir `RESET` antes de eliminar las dos bases locales.

La alternativa Compose permanece en `infra/compose.yaml`, pero no fue usada en
esta validación. Exige definir `POSTGRES_PASSWORD` fuera de Git.

## Migraciones

```bash
make migrate
make migrate-down
make migrate
```

Alembic obtiene la conexión exclusivamente de `DATABASE_URL`.

## Tests

Unitarios, sin PostgreSQL:

```bash
backend/.venv/bin/pytest -c backend/pyproject.toml -m "not postgres" backend/tests
```

Integración PostgreSQL aislada:

```bash
make test-postgres
```

El fixture de pytest rechaza cualquier base distinta de
`faro_politico_test`, cualquier URL sin sufijo `_test` y una URL igual a
`DATABASE_URL`.

## Fixtures ficticios y esquema

```bash
make load-fixtures
make validate-fixtures
make inspect-schema
```

El cargador es idempotente y usa únicamente Persona Ficticia A, Persona Ficticia
B y antecedentes expresamente ficticios. `validate-fixtures` termina con código
distinto de cero si falta una absolución, aparece una condena indebida o existe
un predicado prohibido. `inspect-schema` consulta los catálogos de PostgreSQL
real y muestra tablas, columnas, tipos, constraints, índices, claves foráneas y
acciones `ON DELETE`.

## Verificación completa

```bash
backend/.venv/bin/ruff format --check backend/src backend/tests backend/alembic scripts
backend/.venv/bin/ruff check backend/src backend/tests backend/alembic scripts
backend/.venv/bin/mypy --config-file backend/pyproject.toml backend/src
backend/.venv/bin/pytest -c backend/pyproject.toml -m "not postgres" backend/tests
make test-postgres
make migrate-down
make migrate
DATABASE_URL="$DATABASE_URL" backend/.venv/bin/alembic -c backend/alembic.ini check
make validate-fixtures
make inspect-schema
git diff --check
```

No se implementan frontend, API pública, score, Neo4j, inteligencia artificial,
políticos reales ni nuevas fuentes en esta etapa.
