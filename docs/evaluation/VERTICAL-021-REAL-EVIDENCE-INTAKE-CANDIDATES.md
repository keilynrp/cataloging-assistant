# VERTICAL-021 Real Evidence Intake Candidates

**Estado:** PRE-AUTHORIZATION CANDIDATE SET — no evidencia real autorizada ha sido materializada ni adjudicada.

Baseline: `main` @ `909aac81f4d97106231d77c014f19ab0d38c07b1`.

## 1. Propósito

Registrar un conjunto inicial de fuentes reales previamente utilizadas o pendientes en el trabajo catalográfico para evaluar su incorporación al Golden Set humano de VERTICAL-021, sin convertir su mera disponibilidad pública o su presencia en la cola catalográfica en autorización de uso para evaluación.

## 2. Candidatos

### Candidato 001

- Título: *Spatial Language and the Use of Body-Part Terms in Nahuatl and P’urhepecha*.
- Autor: Martha Mendoza.
- Localizador: `http://journals.linguisticsociety.org/proceedings/index.php/BLS/article/view/1174`.
- Estado: `PENDING_EXPLICIT_USER_AUTHORIZATION`.
- Snapshot local: no materializado.
- Revisores: no asignados.

### Candidato 002

- Título: *Lenguas europeas y lenguas mexicanas: actitudes lingüísticas de universitarios en Guadalajara (México)*.
- Autores: Martha Islas; Alfredo Leonardo Romero Sánchez; Nicolás Lozano Mercado.
- Localizador: `http://www.cunorte.udg.mx/puntocunorte/sites/default/files/Revista%209.%20Arti%CC%81culo%208.pdf`.
- Estado: `PENDING_EXPLICIT_USER_AUTHORIZATION`.
- Snapshot local: no materializado.
- Revisores: no asignados.

### Candidato 003

- Título: *La construcción de la identidad p’urhepecha a partir de la educación intercultural iling e propia*.
- Autores: R. E. Hamel; A. E. E. Baltazar; B. M. Escamilla.
- Localizador: `https://doi.org/10.30972/riie.15207253`.
- Estado: `PENDING_EXPLICIT_USER_AUTHORIZATION`.
- Snapshot local: no materializado.
- Revisores: no asignados.

## 3. Scope de evaluación previsto

El conjunto se propone para evaluar, cuando la evidencia real lo soporte, los cinco bindings lingüísticos críticos:

- `linguistic-family` → `dc.subject.linguisticFamily`;
- `linguistic-branch` → `dc.subject.linguisticBranch`;
- `linguistic-group` → `dc.subject.linguiscgroup`;
- `linguistic-variant` → `dc.subject.linguisticVariant`;
- `registered-language` → `dc.description.registeredLanguage`.

La inclusión de un binding en el scope no presupone que una fuente contenga evidencia suficiente para ese campo. La inspección del snapshot determina el scope efectivo.

## 4. Gate de entrada a revisión humana

Ningún candidato puede pasar a `READY_FOR_INDEPENDENT_REVIEW` hasta que se cumplan simultáneamente:

1. autorización explícita para usar la fuente en evaluación local;
2. snapshot o representación local inmutable con SHA-256 real;
3. inspección de la fuente para fijar bindings bajo revisión y selectores reproducibles;
4. asignación de dos catalogadores distintos;
5. ausencia de secretos o datos no autorizados en los artefactos persistidos.

Hasta entonces, el conjunto permanece fuera de los denominadores semánticos empíricos y no puede contribuir a un cierre de Gate D.

## 5. Qué no hace este artefacto

No descarga fuentes, no persiste documentos reales, no afirma licencias, no autoriza data egress, no activa proveedores LLM, no crea candidatos runtime, no adjudica valores, no convierte ninguna evidencia en `VERIFICADO` y no escribe en DSpace.
