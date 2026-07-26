# Contrato de datos de Cámara para la V0

Última comprobación real: 25 de julio de 2026 (America/Santiago).

## Decisión ejecutiva

El contrato de Open Data de la Cámara está incompleto para resolver
territorialmente a los diputados vigentes:

- `retornarDiputadosPeriodoActual` devuelve 155 `DiputadoPeriodo`, pero ninguno
  contiene `Distrito`, `Distrito/Numero` ni `Distrito/Comunas`;
- el resultado es idéntico para HTTP GET y HTTP POST;
- SOAP 1.1 y SOAP 1.2 también omiten los tres nodos;
- `retornarDiputadosXPeriodo` ya había mostrado la misma omisión.

Por tanto, la V0 no debe publicar pertenencia territorial desde Open Data hasta
que la fuente reponga el campo o se apruebe expresamente otra fuente productiva.
No se usarán nombres hardcodeados.

El ID del diputado sí es consistente entre el listado vigente, asistencia y
voto individual, y se adopta como clave oficial de resolución de entidades.

No se encontró una relación explícita entre sesión y votación. En consecuencia,
`Votacion.session_id` será nullable. Una coincidencia temporal no se almacenará,
publicará ni tratará como relación confirmada.

## Operaciones y protocolos comprobados

Todos los endpoints XML pertenecen a
`https://opendata.camara.cl/camaradiputados/WServices`.

| Operación | Protocolos reales | Parámetros | Campos relevantes realmente presentes |
|---|---|---|---|
| `retornarDiputadosPeriodoActual` | GET, POST form, SOAP 1.1, SOAP 1.2 | ninguno | `DiputadoPeriodo`, fechas, `Diputado/Id`, identidad y militancias. Sin `Distrito`. |
| `retornarPeriodoLegislativoActual` | GET | ninguno | período ID 11, legislatura ID 58, fechas y tipo. |
| `retornarLegislaturas` | GET | ninguno | colección de legislaturas; permitió seleccionar explícitamente la anterior, ID 57. |
| `retornarSesionesXLegislatura` | GET | `prmLegislaturaId` | sesiones con ID, número, fechas, tipo y estado. |
| `retornarSesionesXAnno` | GET | `prmAnno` | misma estructura general de sesiones. |
| `retornarSesionAsistencia` | GET y SOAP 1.1 | `prmSesionId` | sesión y `ListadoAsistencia`; sin `Votaciones` en las muestras. |
| `retornarVotacionesXAnno` | GET | `prmAnno` | eventos con ID, fecha, descripción, totales y tipos; sin sesión. |
| `retornarVotacionDetalle` | GET | `prmVotacionId` | evento y votos individuales asociados por `Diputado/Id`; sin sesión. |

Todas las consultas aplican timeout, User-Agent identificable,
`raise_for_status()` y preservación byte a byte de la respuesta con SHA-256.

## Auditoría territorial cruda

Conteos obtenidos directamente con XPath sobre cada XML completo, antes de
usar el parser:

| Protocolo | DiputadoPeriodo | Distrito | Distrito/Numero | Distrito/Comunas |
|---|---:|---:|---:|---:|
| HTTP GET | 155 | 0 | 0 | 0 |
| HTTP POST form | 155 | 0 | 0 | 0 |
| SOAP 1.1 | 155 | 0 | 0 | 0 |
| SOAP 1.2 | 155 | 0 | 0 | 0 |

El XSD y los ejemplos de la página ASMX declaran
`DiputadoPeriodo/Distrito/{Numero,Comunas}`. Es un campo documentado pero
ausente en producción.

## Validación territorial externa

Se investigaron únicamente fuentes oficiales del Congreso:

1. El Reporte Distrital 2026 de la Biblioteca del Congreso Nacional responde
   `200` como HTML server-rendered y confirma cinco diputados para el Distrito
   19. Los cinco nombres se pudieron resolver, solo como validación, contra
   IDs del listado Open Data: `1197`, `1143`, `1116`, `1204` y `1119`.
2. El reporte BCN no incluye el ID oficial de Cámara ni expone en la página una
   API estructurada documentada. El HTML supera 1 MB y su tabla no constituye
   un contrato estable de datos.
3. Las fichas públicas de `camara.cl` muestran distrito y un parámetro `prmId`,
   pero las peticiones automatizadas desde este entorno reciben `403` de
   Cloudflare.

Decisión: BCN sirve para comprobar que se esperan cinco representantes, pero no
se convierte automáticamente en fuente productiva. La coincidencia por nombre
queda en el resumen como validación diagnóstica, no como cadena publicable.

Como evidencia de consistencia, el ID `1197`, obtenido al cruzar la validación
BCN con el listado oficial, apareció también en asistencia y en el detalle de
una votación. Esto valida el ID como clave de entidad, pero no subsana el campo
territorial ausente en Open Data.

## Auditoría sesión–votación

Se inspeccionaron:

- sesiones recientes `4804`, `4803` y `4802` de la legislatura 58;
- tres sesiones celebradas de 2025 pertenecientes a la legislatura anterior
  57;
- cada detalle mediante HTTP GET y SOAP 1.1;
- los listados `retornarSesionesXLegislatura` y
  `retornarSesionesXAnno`;
- las respuestas completas de `retornarVotacionesXAnno` y
  `retornarVotacionDetalle`.

En las doce respuestas de detalle controladas:

- `Votaciones` no apareció;
- no apareció vacío;
- no apareció ningún `Votacion/Id`;
- GET y SOAP 1.1 coincidieron en esa ausencia.

El XSD declara `SesionSala/Votaciones` como opcional. El fixture
`documented_session_with_votes.xml` representa únicamente esa forma
documentada y está rotulado como tal; no es una respuesta observada.

El detalle real de votación tampoco contiene `Sesion` ni `session_id`. No se
encontró una clave explícita en ninguna dirección.

## Contrato recomendado para la V0

### Diputado

- `official_id: str`: obligatorio, tomado de `Diputado/Id`; clave de resolución.
- `name_original: str`: obligatorio.
- `district: int | null`: nullable mientras Open Data omita el nodo.
- `district_source_operation: str | null`: obligatorio cuando exista distrito.
- Publicación para un distrito: bloqueada si `district` es null.

### Asistencia

- `session_id: str`: obligatorio.
- `deputy_official_id: str`: obligatorio; FK lógica a `Diputado.official_id`.
- `raw_status: str`: obligatorio y preservado sin interpretación.
- `source_url` y hash de evidencia: obligatorios.

### Votación y voto individual

- `vote_event_id: str`: obligatorio.
- `session_id: str | null`: nullable; solo se completa si una respuesta oficial
  incorpora una clave explícita.
- `deputy_official_id: str`: obligatorio en voto individual.
- `raw_option: str`: obligatorio y preservado sin interpretación.
- `temporal_candidate`: no forma parte del contrato productivo.

## Relaciones confirmadas

- período → legislatura por `PeriodoLegislativo/Legislaturas/Legislatura/Id`;
- legislatura → sesión por parámetro y respuesta de
  `retornarSesionesXLegislatura`;
- sesión → asistencia por `retornarSesionAsistencia(prmSesionId)`;
- asistencia → diputado por `Diputado/Id`;
- evento de votación → voto individual por `Votacion/Votos/Voto`;
- voto individual → diputado por `Diputado/Id`.

## Relaciones no confirmadas

- diputado vigente → distrito en las respuestas Open Data actuales;
- sesión → votación;
- votación → sesión;
- nombre BCN → ID Cámara como relación productiva estable.

## Hechos, ausencias del contrato e inferencias prohibidas

### Hechos

- Los cuatro protocolos de diputados respondieron HTTP 200.
- Todos retornaron 155 `DiputadoPeriodo`.
- Asistencia y voto individual contienen IDs de diputado coincidentes.
- BCN reporta cinco diputados para el Distrito 19.

### Ausencias del contrato

- `DiputadoPeriodo/Distrito`, aunque está documentado.
- `SesionSala/Votaciones` en todas las muestras reales auditadas.
- `session_id` en las respuestas reales de votación.

### Inferencias prohibidas

- asignar distrito por nombre, partido, región, correo o conocimiento externo;
- convertir la coincidencia de timestamp en vínculo sesión–votación;
- llenar `Votacion.session_id` con un `temporal_candidate`;
- publicar la validación BCN como fuente productiva sin una decisión explícita
  y una evaluación de estabilidad;
- interpretar asistencia, ausencia u opción de voto como conducta correcta o
  incorrecta.

## Reproducción

```bash
cd backend
source .venv/bin/activate
cd ..
python scripts/explore_camara.py --district 19 --timeout 60
```

Mientras Open Data continúe omitiendo el distrito, el resultado esperado es
`status: incomplete_source_contract` y código de salida `2`. Todos los XML y el
HTML BCN se guardan íntegros en `data/raw` con operación, protocolo, fecha UTC y
prefijo del SHA-256 en el nombre; el resumen imprime el hash completo.
