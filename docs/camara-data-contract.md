# Spike del contrato Open Data de la Cámara

Fecha de comprobación real: 25 de julio de 2026.

## Resultado

La fuente permite recuperar período, legislatura, sesiones, asistencia,
votaciones y votos individuales. No permite completar de forma verificable la
cadena para el Distrito 19 en su estado actual: las respuestas reales omiten la
relación entre `DiputadoPeriodo` y `Distrito`, aunque la documentación y el XSD
la declaran.

No se infirieron nombres ni distritos y no se usó otra fuente para rellenar la
ausencia.

## Servicios inspeccionados

- `WSDiputado.asmx?WSDL`
- `WSLegislativo.asmx?WSDL`
- `WSSala.asmx?WSDL`
- servicio consolidado legado `wscamaradiputados.asmx?WSDL`
- esquema oficial `camaradiputados/v1/camaradiputados.xsd`

Todos pertenecen a `https://opendata.camara.cl`.

## Operaciones y dependencias

| Información | Operación y URL | Método y parámetros | Respuesta real general | Depende de |
|---|---|---|---|---|
| Diputados vigentes por período | `WSDiputado.asmx/retornarDiputadosXPeriodo` | GET, `prmPeriodoID` entero; también documenta POST form y SOAP | `DiputadosPeriodoColeccion/DiputadoPeriodo/{FechaInicio, FechaTermino, Diputado}`. En la respuesta observada falta `Distrito`. | ID de `retornarPeriodoLegislativoActual` |
| Diputados vigentes (alternativa) | `WSDiputado.asmx/retornarDiputadosPeriodoActual` | GET sin parámetros; también POST/SOAP | Misma colección, pero observada sin `Distrito` y con fechas anómalas. | Ninguna |
| Períodos | `WSLegislativo.asmx/retornarPeriodosLegislativos` | GET sin parámetros; también POST/SOAP | `PeriodosLegislativosColeccion/PeriodoLegislativo`, con ID, nombre, fechas y legislaturas. | Ninguna |
| Período actual | `WSLegislativo.asmx/retornarPeriodoLegislativoActual` | GET sin parámetros; también POST/SOAP | Un `PeriodoLegislativo` con `Id`, nombre, fechas y legislaturas. El 25-07-2026 retornó período 11. | Ninguna |
| Legislaturas | `WSLegislativo.asmx/retornarLegislaturas` | GET sin parámetros; también POST/SOAP | `LegislaturasColeccion/Legislatura`, con ID, número, fechas y tipo. | Ninguna |
| Legislatura actual | `WSLegislativo.asmx/retornarLegislaturaActual` | GET sin parámetros; también POST/SOAP | Una `Legislatura`. El período actual también incluye este dato; se observó ID 58, número 374. | Ninguna |
| Sesiones | `WSSala.asmx/retornarSesionesXLegislatura` | GET, `prmLegislaturaId` entero; también POST/SOAP | `SesionesSalaColeccion/Sesion`, con ID, número, intervalo, tipo y estado. | ID de legislatura |
| Detalle y asistencia | `WSSala.asmx/retornarSesionAsistencia` | GET, `prmSesionId` entero; también POST/SOAP | `SesionSala` con datos de sesión y `ListadoAsistencia/Asistencia`; cada registro contiene estado original, justificación opcional y diputado. | ID de sesión |
| Votaciones | `WSLegislativo.asmx/retornarVotacionesXAnno` | GET, `prmAnno` entero; también POST/SOAP | `VotacionesColeccion/Votacion`, con ID, descripción, fecha, totales, quorum, resultado y tipo. | Año |
| Detalle de votación | `WSLegislativo.asmx/retornarVotacionDetalle` | GET, `prmVotacionId` entero; también POST/SOAP | Una `Votacion` con metadatos y `Votos/Voto`; cada voto contiene diputado y `OpcionVoto`. | ID de votación |
| Voto individual | Incluido en `retornarVotacionDetalle` | No requiere otra petición | `Voto/Diputado/Id` más `Voto/OpcionVoto`; el texto original se conserva. | Detalle de votación |

Los endpoints HTTP GET retornaron `200 text/xml; charset=utf-8`. El script usa
`raise_for_status()`, timeout explícito y User-Agent identificable.

## Cadena observada y límites

1. `retornarPeriodoLegislativoActual` retornó período ID `11` y legislatura ID
   `58`.
2. `retornarSesionesXLegislatura(58)` retornó 55 sesiones.
3. Las sesiones celebradas consultadas mediante `retornarSesionAsistencia`
   retornaron entre 154 y 155 registros de asistencia.
4. `retornarVotacionesXAnno(2026)` retornó 791 votaciones en la comprobación.
5. `retornarVotacionDetalle(87057)` retornó 155 votos individuales en la
   comprobación exploratoria.
6. La respuesta de votación no contiene ID de sesión. El spike selecciona una
   votación cuyo timestamp cae dentro del intervalo de una sesión y etiqueta
   expresamente esa unión como inferencia temporal, no como relación oficial.
7. La ausencia de `Distrito` impide seleccionar responsablemente un voto de un
   diputado del Distrito 19.

## Diferencias entre documentación y respuesta

- El XSD documenta `DiputadoPeriodo/Distrito` y las páginas ASMX lo muestran en
  ejemplos GET, POST y SOAP. Las respuestas reales de
  `retornarDiputadosXPeriodo` para los períodos 9, 10 y 11 no contienen ningún
  nodo `Distrito`, tanto por GET como por SOAP 1.1.
- `retornarDiputadosPeriodoActual` también omite `Distrito`. El 25-07-2026 su
  primer `DiputadoPeriodo/FechaInicio` fue `2030-03-10T00:00:00`, pese a que el
  período actual retornado por el servicio legislativo comienza en 2026.
- El endpoint consolidado legado
  `getPeriodoLegislativoActual` respondió un elemento con `xsi:nil="true"`,
  mientras el servicio separado retornó correctamente el período 11.
- `getSesionDetalle` del servicio legado respondió elementos `Sesion` con
  `xsi:nil="true"` para sesiones recientes; `WSSala.retornarSesionAsistencia`
  sí retornó sus datos y asistencia.
- El tipo documentado para sesión incluye votaciones en algunos ejemplos, pero
  ninguna de las 55 respuestas de la legislatura 58 consultadas mediante
  `retornarSesionAsistencia` incluyó nodos `Votacion`.

## Reproducción

```bash
cd backend
source .venv/bin/activate
cd ..
python scripts/explore_camara.py --district 19 --timeout 60
```

El código de salida esperado mientras continúe la omisión es `2`, acompañado de
`status: incomplete_source_contract`. Los XML completos se guardan sin
modificar bajo `data/raw`, con el prefijo de operación y los primeros doce
caracteres de su SHA-256. El resumen incluye el SHA-256 completo de cada
respuesta.

Los fixtures de tests son extractos pequeños de respuestas reales y preservan
los nombres de elementos y valores originales relevantes; no sustituyen la
evidencia íntegra guardada en `data/raw`.
