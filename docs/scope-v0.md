# Alcance de Faro Político V0

## Definición

La V0 es un **dossier histórico verificable de 3 a 5 políticos chilenos, con
línea temporal, evidencia documental y relaciones históricas**. Su propósito es
mostrar qué hecho está respaldado por qué documento, qué período cubre y cuál
fue su resultado, sin emitir acusaciones ni clasificaciones morales propias.

No es solo un dashboard de actividad parlamentaria reciente. El módulo Open
Data de la Cámara se conserva como una fuente ya auditada dentro de una
plataforma histórica más amplia.

## Contenido del dossier

- identidades y variantes documentadas;
- cargos, mandatos, militancias y territorios versionados;
- actividad parlamentaria disponible: sesiones, asistencia y votos;
- organizaciones, sociedades y contratos, solo con respaldo suficiente;
- causas judiciales y administrativas, eventos y resultados;
- declaraciones patrimoniales y reuniones de lobby;
- documentos, snapshots, claims, cobertura y trazabilidad de ingestión;
- rectificaciones, absoluciones, sobreseimientos y decisiones posteriores.

La V0 admite ingestión automatizada de fuentes aprobadas y carga manual
revisada. Ambos caminos deben preservar el original, registrar procedencia y
pasar por el mismo flujo:

`discovered → extracted → pending_review → verified → published`

Los estados terminales o posteriores son `rejected`, `corrected` y `archived`.
Publicar no borra estados anteriores ni la evidencia de una rectificación.

## Principios de publicación

El sistema almacena hechos atribuidos a fuentes y documentos, no acusaciones
propias. Una denuncia no es culpabilidad; una investigación no es condena; una
relación no demuestra delito. Solo una resolución oficial competente establece
una condena o sanción, y debe indicarse si está firme.

Toda afirmación apunta a su evidencia. Se conserva tanto el inicio como el
resultado final, incluidas absoluciones, sobreseimientos y rectificaciones. No
se infieren identidades, parentescos, sociedades o delitos por nombres
coincidentes. La falta de datos no se interpreta como mérito ni reproche.

## Interfaz conceptual futura

El dossier tendrá vistas de:

- línea temporal de hechos y vigencias;
- documentos y fragmentos de respaldo;
- causas, roles procesales, eventos y resultados;
- relaciones históricas con evidencia y revisión;
- actividad parlamentaria;
- cobertura por fuente, dimensión y período;
- derecho a rectificación, historial de cambios y respuesta documentada.

## Límites de esta etapa

Esta etapa solo redefine el dominio y las políticas. No implementa SQLAlchemy,
Alembic, PostgreSQL, frontend, score, scraping masivo ni nuevas integraciones.
Tampoco autoriza tratamiento masivo del portal del Poder Judicial.

El score queda fuera de la V0. Sus condiciones mínimas futuras se documentan en
`docs/future-score-principles.md`.
