# Registro conceptual de fuentes

Este registro identifica fuentes candidatas; no confirma acceso, licencia ni
integración. Cada conector requerirá auditoría técnica y jurídica propia,
snapshots, límites de petición y contrato de datos real.

| Fuente | Finalidad | Autoridad | Cobertura estimada | Acceso | Restricciones y cautelas | Nivel esperado | Revisión |
|---|---|---|---|---|---|---|---|
| Cámara de Diputadas y Diputados | mandatos, sesiones, asistencia y votos | fuente oficial primaria | variable por operación; actividad consistente auditada desde 2002 | servicios XML estructurados | contratos reales difieren del XSD; preservar XML | `official_document` | muestras y anomalías |
| Senado | mandatos y actividad legislativa | fuente oficial primaria | por verificar | estructurado y documentos | verificar términos, IDs y cobertura | `official_document` | sí |
| Biblioteca del Congreso Nacional | reseñas, historia política, normas y reportes territoriales | organismo oficial especializado | histórica, variable por colección | APIs, web y documentos | distinguir reseña de documento constitutivo | `official_document` | sí |
| Poder Judicial | causas, actuaciones y decisiones | fuente oficial competente | variable por tribunal, sistema y digitalización | consulta y documentos; acceso por verificar | **no realizar tratamiento masivo sin verificar autorización y condiciones de uso**; datos sensibles y homónimos | `judicial_filing`, `judicial_decision` o `final_judicial_decision` según documento | obligatoria |
| Contraloría General de la República | dictámenes, procedimientos y sanciones administrativas | autoridad oficial | histórica, variable | buscadores, datos y documentos | verificar vigencia, recursos y alcance | `administrative_resolution` | obligatoria |
| Diario Oficial | leyes, actos societarios y publicaciones oficiales | publicación oficial | amplia, según colección digital | documentos y búsqueda | una publicación societaria no prueba vigencia posterior | `official_document` | sí |
| Mercado Público | licitaciones, adjudicaciones, órdenes y contratos | plataforma oficial | según disponibilidad del sistema | APIs/datos estructurados y documentos | distinguir adjudicación, contrato, modificación y pago | `official_document` | sí |
| InfoProbidad | declaraciones de intereses y patrimonio | plataforma oficial | según obligaciones y conservación | estructurado/documental por verificar | datos personales; versiones y rectificaciones | `official_document` | obligatoria |
| Ley del Lobby | audiencias, viajes y donativos declarados | plataforma oficial | desde vigencia del régimen, por verificar | estructurado y web | registro no implica influencia indebida | `official_document` | sí |
| SERVEL | candidaturas, elecciones, partidos y financiamiento | autoridad electoral | variable por proceso | datos y documentos | verificar versiones y límites de reutilización | `official_document` o resolución | sí |
| Archivo Nacional | expedientes y documentos históricos | custodio oficial | histórica, dependiente del fondo | catálogo y consulta manual/digital | contexto archivístico, derechos y digitalización | `official_document` | obligatoria |
| Solicitudes de transparencia | respuestas y documentos no publicados | organismo público que responde | puntual | gestión y carga manual | anonimizar datos protegidos; conservar solicitud y respuesta | según documento entregado | obligatoria |
| Medios periodísticos | localizar antecedentes y orientar solicitudes | fuente secundaria, no autoridad decisoria | variable | web, hemeroteca o manual | no sustituyen sentencia o resolución; derechos de autor y rectificaciones | `media_reference` | obligatoria |

Los documentos históricos pueden requerir carga manual, transcripción y revisión
humana. OCR o extracción automatizada se registra como confianza técnica y
nunca altera el nivel probatorio del documento.

## Requisitos antes de activar una fuente

1. Verificar autoridad, términos de uso, protección de datos y método de acceso.
2. Medir cobertura temporal real con una muestra acotada.
3. Definir IDs, campos originales, estados, resultados y ausencias.
4. Implementar límites, caché, hashes y reproducción offline.
5. Resolver identidad sin depender exclusivamente del nombre.
6. Definir revisión humana, rectificación y política de publicación.
