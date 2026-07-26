# Validación del núcleo sobre PostgreSQL

Fecha: 25 de julio de 2026.

## Entorno y opción elegida

- sistema: Arch Linux rolling, kernel 7.1.4;
- Python: 3.14.6;
- PostgreSQL: 18.4, paquete binario oficial de Arch;
- Docker: no instalado;
- Podman: no instalado;
- systemd: binarios 261 disponibles, pero el bus del sistema no es accesible
  desde el entorno de ejecución;
- herramientas iniciales PostgreSQL: no instaladas;
- escucha final: `127.0.0.1:55432`.

Se eligió una instalación local administrada por el usuario con `pg_ctl`
(opción D). Instalar el paquete del sistema requería una contraseña `sudo` no
disponible; se extrajeron sin privilegios los paquetes oficiales
`postgresql-18.4-1` y `postgresql-libs-18.4-1` en `.local/postgresql/`. El clúster
vive en `.postgres-data/`. Ambas rutas están excluidas de Git.

La instancia solo escucha en loopback y usa autenticación `trust` en este
entorno local aislado. No es una configuración de producción. La aplicación usa
el rol `faro_politico_app`, verificado como `NOSUPERUSER`, `NOCREATEDB` y
`NOCREATEROLE`. Las bases son:

- `faro_politico_dev`;
- `faro_politico_test`.

URL sanitizada:

`postgresql+psycopg://faro_politico_app@127.0.0.1:55432/faro_politico_dev`

No se almacenó ninguna contraseña en Git.

## Migraciones ejecutadas

Contra PostgreSQL real se ejecutó satisfactoriamente:

1. `alembic upgrade head`;
2. `alembic check`;
3. `alembic downgrade base`;
4. `alembic upgrade head`;
5. `alembic check`.

El downgrade eliminó completamente las tablas de dominio y el segundo upgrade
las reconstruyó. Ambos `alembic check` informaron que no existen operaciones
pendientes.

## Estructura observada

`inspect_postgres_schema.py` consultó PostgreSQL y encontró 16 tablas de dominio:

`electoral_territories`, `entities`, `evidence_claims`, `ingestion_runs`,
`judicial_case_persons`, `judicial_cases`, `judicial_events`, `mandates`,
`manual_reviews`, `organizations`, `person_identities`, `persons`,
`political_affiliations`, `public_offices`, `source_documents` y
`source_snapshots`.

Resumen del catálogo observado:

- 166 columnas;
- 16 primary keys UUID;
- 33 foreign keys;
- 42 constraints `CHECK`;
- 5 constraints `UNIQUE`;
- 10 índices informados por el inspector;
- 5 columnas JSONB;
- 17 columnas TIMESTAMPTZ;
- 33 foreign keys con acción `ON DELETE NO ACTION`;
- referencias autorreferentes en documentos, claims y sus reemplazos.

Las columnas JSONB son `evidence_claims.literal_value`,
`ingestion_runs.metadata`, `manual_reviews.metadata`,
`source_documents.metadata` y `source_snapshots.parameters`.

## Constraints y servicios comprobados

Los tests PostgreSQL verificaron:

- tipo de entidad inválido;
- identidad de fuente duplicada;
- claim sin objeto y claim con dos objetos;
- confianza técnica fuera de 0–1;
- revisión sin target o revisor vacío;
- predicados prohibidos y desconocidos;
- fechas históricas inválidas;
- hash SHA-256 inválido;
- borrado de entidades y documentos referenciados;
- ausencia de cascadas destructivas;
- `supersedes_claim_id` válido e inexistente;
- rollback sin residuos después de una transacción fallida;
- doble inserción de `source_key + source_person_id`;
- ciclo completo de servicios de persona, identidad, mandato, causa,
  participación, evento, documento, claim, revisión, publicación, corrección y
  retiro;
- coexistencia de acusación y absolución;
- bloqueo de condena desde prensa, sin participación, con outcome distinto,
  sin revisor o con firmeza incompatible.

Resultado: 27 tests PostgreSQL aprobados. Los 44 tests unitarios se ejecutan sin
PostgreSQL y no evalúan semántica SQL.

## Fixture ficticio

La carga se ejecutó dos veces. La primera creó datos; la segunda informó que el
fixture ya existía y no modificó el dossier.

Conteos:

| Recurso | Cantidad |
|---|---:|
| entities | 11 |
| persons | 2 |
| person_identities | 2 |
| mandates | 2 |
| organizations | 1 |
| judicial_cases | 2 |
| judicial_case_persons | 2 |
| judicial_events | 3 |
| source_documents | 5 |
| evidence_claims | 4 |
| manual_reviews | 4 |

La validación SQL confirmó acusación y absolución de Persona Ficticia A, ausencia
de condena para A, condena final ficticia de B, relación societaria neutral y
ausencia total de predicados prohibidos.

## Diferencias respecto de SQLite

- PostgreSQL usa UUID nativo; SQLite representaba el tipo de forma emulada.
- JSON se materializa como JSONB.
- las fechas con zona son TIMESTAMPTZ reales;
- PostgreSQL aplica los catálogos `CHECK`, claves foráneas y acciones de borrado
  con semántica definitiva;
- la unicidad concurrente se comprobó con transacciones separadas;
- el DDL Alembic es transaccional en PostgreSQL;
- PostgreSQL detectó expectativas incorrectas de expiración ORM en dos tests,
  que fueron corregidas sin relajar constraints.

No se añadieron ramas SQLite al código de producción. SQLite permanece solo en
tests unitarios de reglas de estado existentes; migraciones, constraints e
integración se prueban en PostgreSQL.

## Problemas encontrados y correcciones

- faltaba PostgreSQL real: se instaló una instancia local aislada;
- el socket predeterminado `/run/postgresql` no existía: se configuró bajo
  `.postgres-data/`;
- `DATABASE_URL` tenía fallback: ahora es obligatoria y valida PostgreSQL;
- tests podían recibir una URL insegura: ahora exigen base exacta
  `faro_politico_test`, sufijo `_test` y URL distinta de desarrollo;
- faltaba validar firmeza de `CONVICTED_IN`: una decisión final exige
  participación con firmeza `final`, y una participación revocada se rechaza;
- el fixture no contenía identidades ni eventos: se agregaron dos identidades y
  tres eventos ficticios;
- Compose contenía credencial predeterminada: ahora exige una variable externa.

## Limitaciones

- el clúster local no es un servicio systemd persistente;
- `trust` solo es aceptable por tratarse de loopback y desarrollo aislado;
- Compose sigue siendo alternativa no validada en este entorno;
- no hay autenticación de revisores;
- no se probaron carga, replicación, backup ni alta disponibilidad;
- no se implementaron frontend, API pública, score, nuevas fuentes ni datos
  reales.
