# Faro Político

Plataforma histórica de evidencia pública para construir dossiers verificables
de políticos chilenos. Conserva hechos, documentos, versiones, revisiones y
rectificaciones sin formular acusaciones propias.

La V0 trabaja con 3 a 5 dossiers revisables. El módulo Open Data de la Cámara se
mantiene como una fuente dentro de un dominio más amplio. Consulta
[docs/scope-v0.md](docs/scope-v0.md) y
[docs/evidence-policy.md](docs/evidence-policy.md).

## Requisitos

- Python 3.12 o superior
- Docker con Docker Compose
- PostgreSQL 17 mediante Compose
- Node.js y npm solo para el frontend existente, fuera de esta etapa

## Instalación

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cd ..
cp .env.example .env
```

La configuración predeterminada local usa:

```dotenv
DATABASE_URL=postgresql+psycopg://trama_publica:trama_publica_dev@localhost:5432/trama_publica
```

## PostgreSQL y migraciones

Desde la raíz:

```bash
docker compose -f infra/compose.yaml up -d postgres
cd backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
```

Revertir completamente y volver a crear:

```bash
alembic -c alembic.ini downgrade base
alembic -c alembic.ini upgrade head
```

Detener PostgreSQL sin eliminar el volumen:

```bash
docker compose -f infra/compose.yaml down
```

## Fixtures ficticios

Después de migrar, desde la raíz del repositorio:

```bash
backend/.venv/bin/python scripts/load_fictitious_evidence.py
```

El cargador es idempotente y usa únicamente Persona Ficticia A, Persona Ficticia
B, instituciones, empresas, causas y documentos expresamente ficticios. No es
una fuente de producción.

## Verificación

```bash
backend/.venv/bin/ruff format --check backend/src backend/tests backend/alembic scripts
backend/.venv/bin/ruff check backend/src backend/tests backend/alembic scripts
backend/.venv/bin/mypy --config-file backend/pyproject.toml backend/src
backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests
git diff --check
```

## Estructura relevante

- `backend/src/trama_publica/db/`: modelos, base y sesiones SQLAlchemy.
- `backend/src/trama_publica/domain/`: catálogos, comandos y servicios.
- `backend/alembic/`: migraciones PostgreSQL.
- `backend/tests/`: parsers existentes y dominio de evidencia.
- `scripts/load_fictitious_evidence.py`: dossier demostrativo ficticio.
- `infra/compose.yaml`: PostgreSQL local.
- `docs/data-model.md`: decisiones y diagrama implementado.
- `docs/review-workflow.md`: transiciones y revisión humana.

No se implementan todavía frontend nuevo, API pública, score, Neo4j,
inteligencia artificial ni nuevas fuentes.
