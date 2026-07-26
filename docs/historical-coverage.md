# Cobertura histórica de la Cámara

Fecha de auditoría: 25 de julio de 2026.

Este documento registra lo que devolvieron realmente los servicios oficiales de
Open Data de la Cámara. No supone que el XSD o la documentación describan
correctamente cada respuesta. La evidencia reproducible está en
`data/raw/historical/`: 228 respuestas XML crudas, metadatos con URL, fecha,
código HTTP y SHA-256, el reporte JSON y la matriz Markdown generados.

## Método y límites

Se consultaron `retornarPeriodosLegislativos`, `retornarDiputados`,
`retornarDiputadosXPeriodo`, `retornarSesionesXAnno`,
`retornarSesionesXLegislatura`, `retornarSesionAsistencia`,
`retornarVotacionesXAnno` y `retornarVotacionDetalle`. El intervalo anual
auditado fue 1965–2026. Para limitar peticiones, se descargaron las listas
anuales completas y se inspeccionaron como máximo dos detalles estratificados
por año (primero y último). Por ello, las cantidades de asistencia y votos
individuales de la matriz son registros de la muestra, no totales anuales.

Una respuesta HTTP 200 vacía se clasifica `unavailable`. Un único error de red o
HTTP se conserva como evidencia, pero se clasifica `untested`, nunca
`unavailable`. Los estados permitidos son `available`, `partial`,
`documented_but_missing`, `unavailable` y `untested`.

## Períodos legislativos

| ID | Período | Inicio | Término | Legislaturas | Diputados | Distrito | IDs oficiales | Calidad |
|---:|---|---|---|---:|---:|---|---|---|
| 7 | 1965-1969 | 1965-05-21 | 1969-05-20 | 0 | 0 | unavailable | unavailable | unavailable |
| 1 | 1990-1994 | 1990-03-11 | 1994-03-10 | 9 | — | untested | untested | untested |
| 2 | 1994-1998 | 1994-03-11 | 1998-03-10 | 12 | — | untested | untested | untested |
| 3 | 1998-2002 | 1998-03-11 | 2002-03-10 | 12 | 121 | available | available | available |
| 4 | 2002-2006 | 2002-03-11 | 2006-03-10 | 12 | 121 | available | available | available |
| 5 | 2006-2010 | 2006-03-11 | 2010-03-10 | 12 | 123 | available | available | available |
| 6 | 2010-2014 | 2010-03-11 | 2014-03-10 | 12 | 123 | available | available | available |
| 8 | 2014-2018 | 2014-03-11 | 2018-03-10 | 12 | 121 | available | available | available |
| 9 | 2018-2022 | 2018-03-11 | 2022-03-10 | 12 | 163 | documented_but_missing | available | partial |
| 10 | 2022-2026 | 2022-03-11 | 2026-03-10 | 12 | 157 | documented_but_missing | available | partial |
| 11 | 2026-2030 | 2026-03-11 | 2030-03-10 | 12 | 155 | documented_but_missing | available | partial |

Los períodos 1 y 2 produjeron HTTP 500 en
`retornarDiputadosXPeriodo`; los cuerpos de error y sus hashes fueron
conservados. El período declarado más antiguo es 1965–1969, pero la operación
entrega una colección vacía. El primer padrón de diputados utilizable es
1998–2002.

Para los períodos 3 a 8, cada diputado trae `Distrito` y `Comunas`; no se
observaron nodos `Circunscripcion` ni `Region`. En los períodos 9 a 11 el
distrito está documentado, pero ausente en las respuestas reales. La
`Militancia` aparece, con cardinalidad variable, en todos los padrones no vacíos.

## Matriz anual representativa

| Período/Año | Diputados | Distrito | Sesiones | Asistencia | Votaciones | Voto individual | Calidad |
|---|---|---|---|---|---|---|---|
| 1965 | untested | untested | unavailable | unavailable | unavailable | unavailable | unavailable |
| 1969 | untested | untested | unavailable | unavailable | unavailable | unavailable | unavailable |
| 1970 | untested | untested | unavailable | unavailable | unavailable | unavailable | unavailable |
| 1989 | untested | untested | unavailable | unavailable | unavailable | unavailable | unavailable |
| 1990 | untested | untested | available | partial | unavailable | unavailable | partial |
| 2001 | untested | untested | available | partial | unavailable | unavailable | partial |
| 2002 | untested | untested | available | available | available | available | available |
| 2003 | untested | untested | available | available | available | available | available |
| 2006 | untested | untested | available | available | available | available | available |
| 2010 | untested | untested | available | available | available | available | available |
| 2014 | untested | untested | available | available | available | available | available |
| 2018 | untested | untested | available | available | available | available | available |
| 2022 | untested | untested | available | available | available | available | available |
| 2025 | untested | untested | available | available | available | available | available |
| 2026 | untested | untested | available | available | available | available | available |

La búsqueda acotada encontró sesiones desde 1990. En las muestras de
1990–2001 no apareció asistencia individual, por lo que ese campo queda
`partial`, no ausente de forma concluyente. La primera evidencia positiva de
asistencia, votaciones y voto individual es 2002.
`retornarSesionesXLegislatura` también devolvió 22 sesiones para la legislatura
319 (ID 3, 1990) y 55 para la legislatura vigente muestreada (ID 58).

## Identidad histórica

`retornarDiputados` entregó 633 IDs únicos; los padrones por período, 549. Todos
los IDs de los padrones estaban contenidos en el catálogo general. Se
encontraron 302 IDs presentes en más de un período. El ID oficial, no el nombre,
es la clave confirmada de continuidad.

Tres casos de múltiples mandatos, seleccionados por cantidad de apariciones:

| ID oficial | Nombre original | Períodos | Catálogo | Asistencia muestreada | Voto muestreado | Resultado |
|---:|---|---|---|---|---|---|
| 843 | René Manuel García García | 3, 4, 5, 6, 8, 9, 11 | sí | sí | sí | ID consistente |
| 855 | Carlos Abel Jarpa Wevar | 3, 4, 5, 6, 8, 9 | sí | sí | sí | ID consistente |
| 862 | Pablo Lorenzini Basso | 3, 4, 5, 6, 8, 9 | sí | sí | sí | ID consistente |

Los nombres fueron comparados para detectar anomalías, pero no se usaron para
resolver identidad. Si dos operaciones entregan IDs diferentes, el sistema solo
puede generar un candidato de correspondencia para revisión manual; nunca una
confirmación automática.

## Territorio histórico versionado

El Distrito 19 actual no se aplica retroactivamente. Un número histórico se
preserva dentro del período y sistema electoral que lo originó, sin convertirlo
al mapa vigente. El contrato conceptual recomendado es:

| Campo | Significado |
|---|---|
| `type` | `distrito`, `circunscripcion`, `region`, `comuna` u otro valor original |
| `number` | número original, nullable |
| `name` | nombre original, nullable |
| `valid_from` | inicio de vigencia conocido, nullable |
| `valid_to` | término de vigencia conocido, nullable |
| `source` | operación/URL oficial y snapshot |

Las comunas deben conservarse como elementos originales asociados al territorio.
La ausencia de territorio en 2018–2030 no autoriza inferencias por nombre,
partido ni trayectoria anterior.

## Decisión para el MVP histórico

| Alternativa | Exactitud e identidad | Cobertura | Validación manual | Decisión |
|---|---|---|---|---|
| A. Actuales, trayectoria disponible | buena, pero sesga el universo | variable | media | expansión posterior |
| B. Período completo, múltiples años | buena desde 2002 | amplia | costosa | segunda fase |
| C. Vinculados históricamente a Ñuble | territorio discontinuo | incierta | costosa | no recomendada inicialmente |
| D. 3–5 personas con varios mandatos | IDs comprobables | 2002–2026 | alta | recomendada |

Se recomienda D para demostrar una trayectoria verificable de extremo a extremo,
con rango inicial 2002–2026. Es el intervalo más amplio con evidencia positiva
consistente de sesiones, asistencia, votaciones y voto individual. Después de
validarlo manualmente puede ampliarse hacia B. El padrón 1998–2002 sirve para
biografía y mandato, pero la actividad completa comienza en 2002.

El producto debe separar:

- historia biográfica: identidad y atributos originales con su fuente;
- historia de cargos: mandato, período, militancia y territorio versionado;
- historia de asistencia: sesión y estado original;
- historia de votaciones: evento y opción individual original, sin inventar
  vínculo sesión-votación;
- historia futura: patrimonio, contratos, lobby y sanciones, fuera de esta
  fuente y de esta etapa.

## Reproducción

```bash
backend/.venv/bin/python scripts/audit_historical_coverage.py \
  --from-year 1965 --to-year 2026 \
  --sample-years 2026 2025 2022 2018 2014 2010 2006 2003 2002 \
  --max-sessions 2 --max-votes 2 --offline
```

El script genera `historical-coverage-report.json` y
`historical-coverage-matrix.md`. El reporte enlaza cada conclusión con la clave
de snapshot correspondiente; el archivo `.meta.json` asociado contiene la URL y
el SHA-256.
