# Política de evidencia

## Principios

Una evidencia respalda una afirmación acotada; no autoriza conclusiones más
amplias. Cada claim debe indicar fuente, documento, fragmento, vigencia, nivel,
estado de revisión y rectificaciones. Se preservan el archivo original y su
snapshot verificable.

La publicación exige lenguaje proporcional: “figura como”, “se presentó” o
“resolvió”, según lo que el documento realmente demuestre. La confianza técnica
mide la calidad de extracción o correspondencia; nunca determina culpabilidad,
firmeza ni otra categoría jurídica.

## Niveles controlados

| Nivel | Qué demuestra | Qué no demuestra | Publicación | Score futuro | Revisión humana |
|---|---|---|---|---|---|
| `unverified_reference` | Existe una referencia aún no corroborada y una pista de búsqueda | Que el hecho referido ocurrió o que la identidad coincide | No como hecho; solo cola interna de descubrimiento | Nunca | Obligatoria |
| `media_reference` | Un medio publicó una afirmación en una fecha | La verdad del hecho, una condena o una sanción oficial | Solo como referencia atribuida y claramente etiquetada; no como conclusión | Nunca | Obligatoria antes de cualquier publicación |
| `official_document` | Un organismo oficial emitió o conserva el documento y los datos expresos que contiene | Que toda alegación contenida esté probada o que exista resultado final | Sí, con contexto, vigencia y atribución | Solo si expresa un hecho verificado elegible por metodología futura | Obligatoria para claims sensibles |
| `administrative_resolution` | Una autoridad administrativa resolvió lo indicado, dentro de su competencia | Firmeza judicial, delito o responsabilidad fuera del alcance resuelto | Sí, indicando estado, recursos y vigencia | Potencialmente, solo verificada y según firmeza/metodología | Obligatoria |
| `judicial_filing` | Una parte presentó una acción, alegación o solicitud en una causa | Que el tribunal la aceptó, que sea verdadera o que exista culpabilidad | Sí solo cuando sea necesario, con rol, estado y advertencia explícita | Nunca por sí sola | Obligatoria |
| `judicial_decision` | Un tribunal dictó la decisión y resultado expresos | Que esté firme o no pueda ser revocada | Sí, indicando tribunal, fecha, resultado y firmeza pendiente o conocida | Potencialmente; nunca tratar como firme si no lo es | Obligatoria |
| `final_judicial_decision` | Una decisión judicial firme o ejecutoriada establece el resultado descrito | Hechos, personas o períodos fuera de lo resuelto | Sí, con alcance exacto y acceso a la decisión | Potencialmente conforme a metodología versionada | Obligatoria |

“Puede publicarse” no significa publicación automática. También se exige
identidad resuelta, licitud de uso, minimización de datos personales, contexto y
revisión según sensibilidad.

## Rectificación y resultado

Un claim no se sobrescribe silenciosamente. Una corrección referencia al claim
anterior, explica el cambio, registra fecha y documento, y puede cambiar el
estado a `corrected` o `archived`. Decisiones revocadas, absoluciones,
sobreseimientos y sanciones dejadas sin efecto permanecen visibles en su
secuencia temporal con el resultado final destacado.

## Flujo de revisión

| Estado | Significado |
|---|---|
| `discovered` | referencia localizada, todavía no extraída |
| `extracted` | contenido y metadatos capturados |
| `pending_review` | espera validación de identidad, fuente, contexto y alcance |
| `verified` | revisión aprobó que el claim corresponde a la evidencia |
| `rejected` | evidencia insuficiente, identidad incorrecta o claim no respaldado |
| `published` | claim verificado visible con su evidencia |
| `corrected` | claim publicado fue rectificado con trazabilidad |
| `archived` | no vigente o retirado, conservado para auditoría |
