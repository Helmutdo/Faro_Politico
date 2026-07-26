# Fixtures Cámara

- `diputados_periodo_without_district.xml`, `session_attendance.xml` y
  `vote_detail.xml` son extractos pequeños de respuestas oficiales observadas.
- `documented_deputies_with_district.xml` y
  `documented_session_with_votes.xml` son fixtures sanitizados de las formas
  opcionales declaradas por el XSD. Sus IDs y nombres son ficticios y están
  rotulados como contrato documentado; esas formas no aparecieron en las
  respuestas reales auditadas.
- `historical_periods.xml` es un extracto pequeño y sanitizado de la estructura
  real de períodos y sus referencias oficiales a legislaturas.

Los XML íntegros, sus protocolos, fechas y SHA-256 quedan en `data/raw` y no se
versionan.
