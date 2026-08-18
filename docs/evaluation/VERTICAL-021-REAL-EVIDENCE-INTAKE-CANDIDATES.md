# VERTICAL-021 Real Evidence Intake Candidates

**Estado:** PARTIAL READY FOR INDEPENDENT REVIEW — dos revisores humanos confirmados; candidato 003 admitido para revisión independiente de `registered-language`; candidatos 001 y 002 permanecen bloqueados para intake.

Baseline: `main` @ `909aac81f4d97106231d77c014f19ab0d38c07b1`.

## 1. Propósito

Registrar un conjunto inicial de fuentes reales para su incorporación controlada al Golden Set humano de VERTICAL-021. La autorización aplica únicamente a evaluación local: no implica data egress, adjudicación, activación de proveedor LLM ni permiso de escritura DSpace.

## 2. Autorización y confirmación humana

El usuario autorizó las tres fuentes para evaluación local el 2026-08-17. Posteriormente confirmó y dio luz verde a que dos personas reales ocupen los slots seudónimos de revisión independiente:

- `cataloger-a` — `independent_reviewer_1`;
- `cataloger-b` — `independent_reviewer_2`.

La confirmación significa asignación humana real a esos roles, no revisión ya realizada. Los resultados de revisión deberán materializarse por separado conforme al protocolo de adjudicación.

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
- Representación local inmutable: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.txt`.
- SHA-256: `f4baeb9fea9e552969532cd5de9f7eaee072590c6505203f66087dfa5b22f3c5`.
- Revisores: confirmados (`cataloger-a`, `cataloger-b`).
- Binding admitido: `registered-language` → `dc.description.registeredLanguage`.
- Intake: `READY_FOR_INDEPENDENT_REVIEW`.

La evidencia preservada muestra P’urhepecha como lengua primera/nativa y español como L2. El scope de revisión queda limitado a `registered-language`. La expresión `Meseta Tarasca` no se usa como evidencia de familia lingüística.

El intake de revisión quedó materializado en:

`apps/api/tests/golden/llm-evidence/human-review/intake/real-evidence-candidate-003.intake.json`

Ese artefacto no contiene juicios humanos todavía; `completed_reviews` permanece vacío.

## 4. Gate

A partir de la confirmación humana, el gate permite entrada parcial a revisión independiente únicamente para el candidato 003 y su binding `registered-language`.

Persisten como bloqueos:

1. candidato 001: snapshot inmutable y verificación de reutilización/licencia;
2. candidato 002: inspección autorizada más completa antes de admitir cualquier binding crítico;
3. antes de `ADJUDICATED_GOLD`: revisiones completas de ambos catalogadores, adjudicación cuando corresponda y SHA-256 real del contrato catalográfico.

## 5. Frontera arquitectónica

Este estado no crea adjudicaciones, no inventa hashes ni resultados humanos, no activa proveedor LLM, no autoriza data egress, no crea candidatos runtime, no convierte evidencia en `VERIFICADO` y no escribe en DSpace.
