# VERTICAL-021 Real Evidence Intake Candidates

**Estado:** AUTHORIZED CANDIDATE SET — candidatos 002 y 003 ya cuentan con representaciones locales inmutables; revisión humana real todavía pendiente.

Baseline: `main` @ `909aac81f4d97106231d77c014f19ab0d38c07b1`.

## 1. Propósito

Registrar un conjunto inicial de fuentes reales para su incorporación controlada al Golden Set humano de VERTICAL-021. La autorización concedida aplica únicamente a evaluación local: no implica data egress, adjudicación, activación de proveedor LLM ni permiso de escritura DSpace.

## 2. Decisión de autorización

El usuario autorizó explícitamente avanzar con las tres fuentes candidatas el 2026-08-17. A partir de esta transición, las tres pueden prepararse para evaluación local, sujetas a evidencia reproducible, inspección de binding y confirmación de dos revisores humanos independientes.

## 3. Slots de revisión reservados

Se reservan los identificadores operativos:

- `cataloger-a` — `independent_reviewer_1`;
- `cataloger-b` — `independent_reviewer_2`.

Estos IDs son **slots seudónimos**, no identidades ni revisiones humanas ya realizadas. Ningún caso puede considerarse `ADJUDICATED_GOLD` hasta que dos personas reales sean confirmadas para ocupar esos slots y ejecuten las revisiones independientes previstas por el protocolo.

## 4. Reconciliación y materialización de fuentes

### Candidato 001

- Título: *Spatial Language and the Use of Body-Part Terms in Nahuatl and P’urhepecha*.
- Autor: Martha Mendoza.
- Localizador canónico: `https://journals.flvc.org/floridalinguisticspapers/article/view/116771`.
- Estado: `AUTHORIZED_LOCAL_EVALUATION`.
- Licencia/reutilización: pendiente de verificación antes de persistir contenido fuente en el repositorio.
- Snapshot local: no materializado.
- Revisores: slots `cataloger-a` y `cataloger-b` reservados, pendientes de confirmación humana real.

### Candidato 002

- Título: *Lenguas europeas y lenguas mexicanas: actitudes lingüísticas de universitarios en Guadalajara (México)*.
- Autores: Martha Islas; Alfredo Leonardo Romero Sánchez; Nicolás Lozano Mercado.
- Localizador canónico: `https://revistas.cunorte.udg.mx/punto/article/view/75`.
- DOI: `10.32870/punto.v1i9.75`.
- Estado: `AUTHORIZED_LOCAL_EVALUATION`.
- Licencia verificada en la página editorial: `CC BY-NC 4.0`.
- Representación local inmutable: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-002.txt`.
- SHA-256: `b7c6fbc726441695d47aba958700c69527877585f6d4e32d2d0a2cd2cad9f01a`.
- Completitud: metadatos editoriales + resumen + declaración de licencia; **no** copia completa del artículo.
- Scope crítico: ningún binding confirmado con seguridad a partir de esta representación parcial.

### Candidato 003

- Título: *La construcción de la identidad p’urhepechas a partir de la educación intercultural bilingüe propia*.
- Autores: Rainer Enrique Hamel; Ana Elena Erape Baltazar; Betzabé Márquez Escamilla.
- Localizador canónico: `https://periodicos.sbu.unicamp.br/ojs/index.php/tla/article/view/8653739`.
- DOI: `10.1590/010318138653739444541`.
- Estado: `AUTHORIZED_LOCAL_EVALUATION`.
- Licencia verificada en la página editorial: `CC BY`.
- Representación local inmutable: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.txt`.
- SHA-256: `f4baeb9fea9e552969532cd5de9f7eaee072590c6505203f66087dfa5b22f3c5`.
- Completitud: fragmentos exactos seleccionados de la representación textual del PDF editorial.
- Scope confirmado para revisión humana: `registered-language` → `dc.description.registeredLanguage`.
- Scope no confirmado: `linguistic-family`, `linguistic-branch`, `linguistic-group`, `linguistic-variant`.

La mención `Meseta Tarasca` se trata como referencia geográfica/cultural en este artefacto y **no** como evidencia automática de `dc.subject.linguisticFamily`.

## 5. Gate de entrada a revisión humana

El conjunto completo todavía no puede pasar a `READY_FOR_INDEPENDENT_REVIEW`. Permanecen abiertos:

1. confirmación real de dos catalogadores humanos distintos para ocupar `cataloger-a` y `cataloger-b`;
2. para candidato 001, licencia/reutilización y snapshot si finalmente se admite;
3. para candidato 002, inspección de una representación más completa antes de admitir cualquier binding crítico;
4. para candidato 003, confirmación humana del scope `registered-language` antes de generar decisiones de revisión.

Los hashes registrados identifican exactamente las representaciones locales persistidas y no se presentan como hashes de los PDFs completos.

## 6. Qué no hace este artefacto

No crea adjudicaciones, no inventa hashes ni revisiones humanas, no autoriza data egress, no activa proveedores LLM, no crea candidatos runtime, no convierte ninguna evidencia en `VERIFICADO` y no escribe en DSpace.
