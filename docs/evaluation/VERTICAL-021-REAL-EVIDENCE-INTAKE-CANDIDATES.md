# VERTICAL-021 Real Evidence Intake Candidates

**Estado:** PARTIAL HUMAN REVIEW COMPLETE — candidato 003 con doble revisión humana v2 y adjudicación humana registrada; contrato catalográfico congelado por SHA-256; candidatos 001 y 002 permanecen bloqueados para intake.

Baseline: `main` @ `909aac81f4d97106231d77c014f19ab0d38c07b1`.

## 1. Propósito

Registrar un conjunto inicial de fuentes reales para su incorporación controlada al Golden Set humano de VERTICAL-021. La autorización aplica únicamente a evaluación local: no implica data egress, activación de proveedor LLM ni permiso de escritura DSpace.

## 2. Autorización y confirmación humana

El usuario autorizó las tres fuentes para evaluación local el 2026-08-17. Posteriormente confirmó y dio luz verde a que dos personas reales ocupen los slots seudónimos de revisión independiente:

- `cataloger-a` — `independent_reviewer_1`;
- `cataloger-b` — `independent_reviewer_2`.

Para el ciclo `rereview-v2` del candidato 003, ambos revisores completaron juicios independientes sobre el mismo paquete de evidencia enriquecida. Una tercera persona humana, `adjudicator-1`, resolvió la discrepancia formal entre `ACCEPT_WITH_MINOR_EDIT` y `ACCEPT_AS_IS`.

## 3. Estado por candidato

### Candidato 001

- Título: *Spatial Language and the Use of Body-Part Terms in Nahuatl and P’urhepecha*.
- Autor: Martha Mendoza.
- Estado de autorización: `AUTHORIZED_LOCAL_EVALUATION`.
- Revisores: confirmados (`cataloger-a`, `cataloger-b`).
- Snapshot: no materializado.
- Licencia/reutilización: pendiente de verificación.
- Intake: `BLOCKED_FOR_INTAKE`.

No entra todavía a revisión independiente.

### Candidato 002

- Título: *Lenguas europeas y lenguas mexicanas: actitudes lingüísticas de universitarios en Guadalajara (México)*.
- DOI: `10.32870/punto.v1i9.75`.
- Licencia: `CC BY-NC 4.0` verificada en página editorial.
- Representación local inmutable: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-002.txt`.
- SHA-256: `b7c6fbc726441695d47aba958700c69527877585f6d4e32d2d0a2cd2cad9f01a`.
- Revisores: confirmados (`cataloger-a`, `cataloger-b`).
- Binding crítico confirmado desde la representación actual: ninguno.
- Intake: `BLOCKED_FOR_INTAKE`.

La representación actual conserva metadatos editoriales, resumen y licencia, pero no evidencia suficiente para admitir un binding lingüístico crítico.

### Candidato 003

- Título: *La construcción de la identidad p’urhepechas a partir de la educación intercultural bilingüe propia*.
- DOI: `10.1590/010318138653739444541`.
- Licencia: `CC BY` verificada en página editorial.
- Paquete de re-revisión v2: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.rereview-v2.packet.txt`.
- SHA-256 del paquete v2: `2a1ceef24ef537796ed5ec44dc7682a8b900964fd9ea70b9647404ad54817f81`.
- Binding evaluado: `registered-language` → `dc.description.registeredLanguage`.
- Revisores: `cataloger-a`, `cataloger-b`.
- Adjudicador: `adjudicator-1`.
- Decisión humana adjudicada: `ACCEPT_WITH_MINOR_EDIT`.
- Valor final humano: `Purépecha`.
- Abstención: `false`.
- Error codes: ninguno.
- Intake actual: `BLOCKED_FOR_INTAKE` por frontera de gobernanza; la adjudicación canónica permanece `TEMPLATE` hasta una transición explícitamente autorizada a `FINAL`.

La primera ronda, basada en evidencia más estrecha, permanece preservada e inmutable con dos decisiones `RESEARCH_REQUIRED`. El ciclo v2 no reescribe esa historia.

## 4. Contrato catalográfico congelado

El contrato maestro usado para evaluación es `dspace-cataloger-v3.6`, materializado desde `apps/api/src/cataloging_api/cataloging_contract.py`.

Artefacto de identidad:

`apps/api/tests/golden/llm-evidence/catalog-contract-dspace-cataloger-v3.6.sha256.json`

Identidades congeladas:

- Git blob SHA-1 del source: `bdab45fd46b020f76df01ee2fa513aa7f094aeb5`;
- SHA-256 del source UTF-8: `05380a8e49e41ff70749c2bde09b3c4059f87e50707144ae2cad228d4e74391f`;
- SHA-256 autoritativo del contrato para VERTICAL-021: `a68fbf9664b7165ea240508da85167058cd57796fbda9c1a9869986afb0178bb`.

El SHA-256 autoritativo se calcula sobre la serialización JSON canónica de `contract_payload()` con UTF-8, `ensure_ascii=false`, claves ordenadas y separadores compactos. El hash del source se conserva únicamente como ancla adicional de reproducibilidad.

## 5. Gate

Persisten como bloqueos o decisiones pendientes:

1. candidato 001: snapshot inmutable y verificación de reutilización/licencia;
2. candidato 002: inspección autorizada más completa antes de admitir cualquier binding crítico;
3. candidato 003: la decisión humana ya está registrada y el contrato ya está congelado, pero `TEMPLATE` → `FINAL` requiere una autorización explícita separada;
4. `ADJUDICATED_GOLD` sigue siendo una transición posterior y separada; no se deriva automáticamente de la materialización del hash ni de la existencia de una decisión humana.

## 6. Frontera arquitectónica

Este estado no activa proveedor LLM, no autoriza data egress, no crea candidatos runtime, no convierte evidencia en `VERIFICADO` y no escribe en DSpace. La materialización del SHA-256 resuelve la identidad del contrato, pero no altera por sí sola estados de gobernanza.
