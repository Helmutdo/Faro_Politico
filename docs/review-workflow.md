# Flujo de revisión

## Objetivo

Ninguna confianza de extracción publica hechos automáticamente. La revisión
humana valida identidad, alcance del fragmento, categoría documental, vigencia,
resultado y lenguaje proporcional.

## Descubrimiento y extracción

1. `discovered`: existe una referencia, sin afirmar que sea cierta.
2. `extracted`: se preservaron documento, snapshot, hash, campos originales y
   un claim candidato.
3. `pending_review`: el claim se congela para revisión contextual.

El envío a revisión solo se permite desde `discovered` o `extracted` y cambia la
publicación a `review_only`.

## Decisiones humanas

- `approve`: de `pending_review` a `verified` y `publishable`;
- `reject`: de `pending_review` a `rejected/private`;
- `request_changes`: decisión registrable para devolver trabajo, sin aprobación;
- `correct`: conserva el claim anterior como `corrected/withdrawn` y crea otro
  `pending_review/review_only`;
- `archive`: retira un claim publicado como `archived/withdrawn`.

Cada `ManualReview` registra target, identificador del revisor, decisión, notas,
fecha, estado anterior, resultado y metadatos. No hay cuentas ni autenticación
en el MVP, pero el identificador local nunca puede estar vacío.

## Reglas sensibles

`CONVICTED_IN` requiere simultáneamente:

1. `SourceDocument.source_type` igual a `judicial_decision` o
   `final_judicial_decision`;
2. objeto `JudicialCase`;
3. `JudicialCasePerson` del sujeto y la causa con `outcome=convicted`;
4. aprobación humana registrada.

Una referencia periodística, acusación o confianza técnica alta no satisface
estas condiciones. `ACQUITTED_IN`, `DISMISSED_FROM_CASE` y rectificaciones se
conservan como claims propios; no sobrescriben acusaciones anteriores.

## Transiciones bloqueadas

- `discovered → published`;
- `rejected → published`;
- `private → published`;
- aprobación fuera de `pending_review`;
- publicación sin `verified + publishable`;
- condena verificada desde prensa o sin participación condenada;
- corrección que borra el claim anterior;
- revisión sin target o sin identificador de revisor;
- predicados fuera del catálogo, incluidos `CONSPIRED_WITH`,
  `CORRUPT_NETWORK`, `CRIMINAL_ASSOCIATE`, `IS_CORRUPT`, `IS_CRIMINAL` e
  `IS_SUSPICIOUS`.

## Rectificación

El derecho a rectificación produce una nueva revisión y mantiene la cadena
`supersedes_claim_id`. El documento anterior, la revisión que permitió su
publicación, el motivo de corrección y el reemplazo permanecen auditables.
