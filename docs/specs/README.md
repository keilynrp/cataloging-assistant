# Vertical specifications index

This directory is the canonical index of the project's vertical specifications. Each vertical defines a bounded functional, technical, evaluation, or operational slice of Cataloging Assistant.

## Status policy

The existence of a specification does **not** by itself mean that the vertical is complete, deployed, accepted, or operationalized. A lifecycle status is shown here only when the repository contains explicit acceptance evidence that supports it. Otherwise, consult the specification and its linked implementation/evaluation artifacts for the current state.

| Vertical | Specification | Lifecycle status |
| --- | --- | --- |
| VERTICAL-001 | [DSpace a ficha](VERTICAL-001-dspace-a-ficha.md) | See specification |
| VERTICAL-002 | [Diagnóstico catalográfico](VERTICAL-002-diagnostico-catalografico.md) | See specification |
| VERTICAL-003 | [Registros similares](VERTICAL-003-registros-similares.md) | See specification |
| VERTICAL-004 | [Evidencia y perfil de colección](VERTICAL-004-evidencia-perfil-coleccion.md) | See specification |
| VERTICAL-005 | [Revisión humana local](VERTICAL-005-revision-humana-local.md) | See specification |
| VERTICAL-006 | [Borrador local versionado](VERTICAL-006-borrador-local-versionado.md) | See specification |
| VERTICAL-007 | [Cola de trabajo](VERTICAL-007-cola-trabajo.md) | See specification |
| VERTICAL-008 | [Vocabularios controlados](VERTICAL-008-vocabularios-controlados.md) | See specification |
| VERTICAL-009 | [Hallazgos de vocabulario](VERTICAL-009-hallazgos-vocabulario.md) | See specification |
| VERTICAL-010 | [Validación de borradores contra vocabulario](VERTICAL-010-validacion-borradores-vocabulario.md) | See specification |
| VERTICAL-011 | [Sugerencias supervisadas](VERTICAL-011-sugerencias-supervisadas.md) | See specification |
| VERTICAL-012 | [Operación de sugerencias](VERTICAL-012-operacion-sugerencias.md) | See specification |
| VERTICAL-013 | [Réplica de vocabularios DSpace](VERTICAL-013-replica-vocabularios-dspace.md) | See specification |
| VERTICAL-014 | [Notificaciones en tiempo real](VERTICAL-014-notificaciones-tiempo-real.md) | See specification |
| VERTICAL-015 | [Agente conversacional](VERTICAL-015-agente-conversacional.md) | See specification |
| VERTICAL-016 | [Modelo lingüístico v3.6](VERTICAL-016-modelo-linguistico-v3-6.md) | See specification |
| VERTICAL-017 | [Ingesta de evidencia externa](VERTICAL-017-ingesta-evidencia-externa.md) | See specification |
| VERTICAL-018 | [Contrato maestro runtime](VERTICAL-018-contrato-maestro-runtime.md) | See specification |
| VERTICAL-019 | [Golden set PDF evidence](VERTICAL-019-golden-set-pdf-evidence.md) | See specification |
| VERTICAL-020 | [Secure remote evidence fetch](VERTICAL-020-secure-remote-evidence-fetch.md) | See specification |
| VERTICAL-021 | [Provider-independent LLM-assisted extraction](VERTICAL-021-provider-independent-llm-assisted-extraction.md) | See specification |
| **VERTICAL-022** | **[DSpace contract drift detection](VERTICAL-022-dspace-contract-drift-detection.md)** | **Accepted / Operationalized** |
| **VERTICAL-023** | **[Production readiness & operational health](VERTICAL-023-production-readiness-operational-health.md)** | **Accepted / Operationalized** |
| VERTICAL-024 | [Operational recovery & restart hardening](VERTICAL-024-operational-recovery-restart-hardening.md) | See specification |

## Current operational milestone

VERTICAL-022 established the governed DSpace contract synchronization path as operational with a human-approved ACTIVE baseline, exact reconciliation, resolution inheritance, and a repository-managed scheduler wrapper that passed a deployed smoke test.

VERTICAL-023 is now also accepted and operationalized. Its durable acceptance evidence verifies production commit identity, API liveness, PostgreSQL-backed readiness, internal frontend reachability, public frontend/API reachability, a governed production smoke result of `PASS` with exit code `0`, and read-only observation of VERTICAL-022 state.

VERTICAL-024 is specified but not yet implemented or operationalized. It addresses the residual recovery risk discovered during VERTICAL-023-C: Catalog Assistant must recover predictably after Docker daemon restart without manual stack restoration while preserving VERTICAL-023 health/readiness semantics and VERTICAL-022/DSpace governance.

Evidence and operations documents:

- [VERTICAL-023 operational acceptance](../vertical-023-operational-acceptance.md)
- [VERTICAL-022 operational acceptance](../vertical-022-operational-acceptance.md)
- [VERTICAL-022 activation runbook](../vertical-022-activation-runbook.md)
- [VERTICAL-022 live contract reconciliation](../vertical-022-live-contract-reconciliation.md)
- [VERTICAL-022 scheduled synchronization](../vertical-022-scheduled-sync.md)

These lifecycle designations do not remove either accepted vertical from governance. Material DSpace contract drift, failed reconciliation, readiness failure, public/internal reachability failure, deployment-identity mismatch, failed automatic recovery, or other documented stop conditions still require human review. Automated operational checks must not approve or promote a DSpace baseline.

## Maintaining this index

When a new vertical is added, add it here in numeric order. Change a lifecycle status only when a durable repository artifact supports the new status. Prefer links to acceptance, evaluation, or operational evidence over prose claims duplicated in this file.
