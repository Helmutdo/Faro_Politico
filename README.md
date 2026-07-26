# Trama Pública

Plataforma de transparencia parlamentaria basada exclusivamente en datos
oficiales verificables. La V0 cubre a las diputadas y los diputados vigentes
del Distrito 19 (Ñuble), usando como única fuente el Open Data de la Cámara de
Diputadas y Diputados de Chile.

## Estado

Este repositorio contiene el esqueleto inicial del monorepo. Todavía no incluye
integración con la Cámara, extracción de datos ni modelos de base de datos.
Consulta [docs/scope-v0.md](docs/scope-v0.md) para conocer el alcance aprobado.

## Estructura

- `backend/`: aplicación Python compartida por API, dominio y futuros procesos ETL.
- `web/`: aplicación Next.js con TypeScript y App Router.
- `infra/`: infraestructura local con Docker Compose.
- `docs/`: decisiones y alcance del producto.
- `scripts/`: automatizaciones del proyecto.
- `data/raw/`: datos originales locales, excluidos de Git salvo su marcador.

## Requisitos

- Python 3.12 o superior
- Node.js 22 o superior y npm
- Docker con Docker Compose
- Git

Versiones detectadas al inicializar el proyecto (25 de julio de 2026):

- Python 3.14.6
- Node.js 26.5.0
- npm 12.0.1
- Git 2.55.0
- Docker y Docker Compose: no disponibles en el entorno

## Instalación

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Frontend:

```bash
cd web
npm install
```

Configuración local:

```bash
cp .env.example .env
```

## Desarrollo

Servicios de infraestructura:

```bash
docker compose -f infra/compose.yaml up -d
```

API:

```bash
cd backend
source .venv/bin/activate
uvicorn trama_publica.api.app:app --reload
```

Frontend:

```bash
cd web
npm run dev
```

## Verificación

```bash
cd backend
ruff format --check .
ruff check .
mypy src
pytest

cd ../web
npm run lint
npm run typecheck
npm run build
```

## Fuente y trazabilidad

La única fuente autorizada para la V0 es el portal Open Data de la Cámara de
Diputadas y Diputados de Chile. Cada dato que llegue a publicarse deberá incluir
su fuente y conservar el valor original recibido.
