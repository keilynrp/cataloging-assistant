# VERTICAL-017: Ingesta controlada de evidencia externa

## Estado

**Especificada; no implementada en este cambio.**

## Objetivo

Llevar a la aplicación el flujo que hoy ejecuta `dspace-cataloger cataloga:` fuera del runtime: recibir una URL y/o un texto completo aportado por el catalogador, extraer evidencia bibliográfica y lingüística, y producir un **borrador de evidencia**, nunca una escritura DSpace.

## Principios

1. DSpace continúa como fuente de verdad para registros ya sincronizados.
2. Una URL, PDF o texto aportado es **fuente de evidencia externa**, no fuente de verdad del repositorio.
3. La extracción debe conservar trazabilidad a fragmentos/páginas/URL.
4. El resultado debe separar `EXTRAÍDO`, `VERIFICADO`, `INFERIDO`, `GENERADO` y `PENDIENTE`.
5. Los vocabularios activos de la aplicación gobiernan la validación final; el skill no puede promover automáticamente sus propios vocabularios.
6. Ninguna salida se aplica a DSpace automáticamente.
7. El agente conversacional read-only de ADR-010 no recibe nuevas herramientas de escritura. La ingesta debe ser un flujo separado, explícitamente iniciado por el catalogador.

## Flujo propuesto

1. Crear una sesión local de evidencia con URL opcional y archivo/texto opcional.
2. Capturar una instantánea inmutable de las fuentes y sus hashes.
3. Extraer metadatos candidatos según el form contract DSpace.
4. Ejecutar reglas deterministas y reconciliación literal contra vocabularios activos.
5. Mostrar una tabla campo/valor/evidencia/estado al catalogador.
6. Permitir que el humano copie valores aprobados hacia un borrador local versionado.
7. Si el registro DSpace cambia durante el proceso, marcar la sesión/borrador como obsoleto mediante `source_hash`.

## Seguridad y límites

- No ejecutar código de archivos aportados.
- No seguir autenticaciones ni sesiones externas del usuario.
- Restringir tamaño, MIME y tiempo de extracción.
- No descargar bitstreams DSpace automáticamente; este flujo trata evidencia externa aportada de forma explícita.
- No afirmar equivalencia entre términos fuente y autoridad si no existe correspondencia aprobada.

## Entidades mínimas propuestas

- `catalog_evidence_sessions`
- `catalog_evidence_sources`
- `catalog_evidence_candidates`
- `catalog_evidence_candidate_values`

Todas con historial append-only o snapshots inmutables donde corresponda.

## API candidata

- `POST /api/evidence-sessions`
- `GET /api/evidence-sessions/{id}`
- `POST /api/evidence-sessions/{id}/extract`
- `GET /api/evidence-sessions/{id}/candidates`
- `POST /api/evidence-sessions/{id}/copy-to-draft`

La última operación crea/revisa únicamente un borrador PostgreSQL y exige `CATALOG_REVIEW_TOKEN`.

## Puertas antes de implementación

P0. Aprobar política de fuentes externas y límites de archivos.
P1. Definir si la extracción inicial será determinista, LLM-assisted o híbrida.
P2. Definir contrato de evidencia por campo y citas de página/fragmento.
P3. Definir reconciliación entre el form contract de 56 bindings y el contrato reducido de borradores lingüísticos.
P4. Añadir fixtures del Golden Set de `dspace-cataloger` como pruebas de aceptación compartidas.
