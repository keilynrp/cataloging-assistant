# VERTICAL-021 Real Evidence Intake Candidates

**Estado:** AUTHORIZED CANDIDATE SET — autorización concedida para evaluación local; snapshots y revisores aún pendientes.

Baseline: `main` @ `909aac81f4d97106231d77c014f19ab0d38c07b1`.

## 1. Propósito

Registrar un conjunto inicial de fuentes reales para su incorporación controlada al Golden Set humano de VERTICAL-021. La autorización concedida aplica únicamente a evaluación local: no implica data egress, adjudicación, activación de proveedor LLM ni permiso de escritura DSpace.

## 2. Decisión de autorización

El usuario autorizó explícitamente avanzar con las tres fuentes candidatas el 2026-08-17. A partir de esta transición, las tres pueden prepararse para evaluación local, sujetas todavía a snapshot inmutable, SHA-256 real, verificación de reutilización cuando corresponda, inspección de binding y asignación de dos revisores independientes.

## 3. Reconciliación de fuentes

### Candidato 001

- Título: *Spatial Language and the Use of Body-Part Terms in Nahuatl and P’urhepecha*.
- Autor: Martha Mendoza.
- Localizador canónico: `https://journals.flvc.org/floridalinguisticspapers/article/view/116771`.
- Estado: `AUTHORIZED_LOCAL_EVALUATION`.
- Licencia/reutilización: pendiente de verificación antes de persistir contenido fuente en el repositorio.
- Snapshot local: no materializado.
- Revisores: no asignados.

El localizador inicialmente registrado apuntaba a otra plataforma. La publicación de 2019 y el localizador FLVC quedan respaldados por la lista institucional de publicaciones de la autora.

### Candidato 002

- Título: *Lenguas europeas y lenguas mexicanas: actitudes lingüísticas de universitarios en Guadalajara (México)*.
- Autores: Martha Islas; Alfredo Leonardo Romero Sánchez; Nicolás Lozano Mercado.
- Localizador canónico: `https://revistas.cunorte.udg.mx/punto/article/view/75`.
- DOI: `10.32870/punto.v1i9.75`.
- Estado: `AUTHORIZED_LOCAL_EVALUATION`.
- Licencia verificada en la página editorial: `CC BY-NC 4.0`.
- Snapshot local: no materializado.
- Revisores: no asignados.

### Candidato 003

- Título: *La construcción de la identidad p’urhepechas a partir de la educación intercultural bilingüe propia*.
- Autores: Rainer Enrique Hamel; Ana Elena Erape Baltazar; Betzabé Márquez Escamilla.
- Localizador canónico: `https://periodicos.sbu.unicamp.br/ojs/index.php/tla/article/view/8653739`.
- DOI: `10.1590/010318138653739444541`.
- Estado: `AUTHORIZED_LOCAL_EVALUATION`.
- Licencia verificada en la página editorial: `CC BY`.
- Snapshot local: no materializado.
- Revisores: no asignados.

El DOI previamente registrado (`10.30972/riie.15207253`) fue descartado porque resuelve a un artículo diferente de 2023, con título y autores distintos. El registro queda reconciliado con la publicación de 2018 en *Trabalhos em Linguística Aplicada*.

## 4. Scope de evaluación previsto

El conjunto se propone para evaluar, únicamente cuando cada snapshot lo soporte, los cinco bindings lingüísticos críticos:

- `linguistic-family` → `dc.subject.linguisticFamily`;
- `linguistic-branch` → `dc.subject.linguisticBranch`;
- `linguistic-group` → `dc.subject.linguiscgroup`;
- `linguistic-variant` → `dc.subject.linguisticVariant`;
- `registered-language` → `dc.description.registeredLanguage`.

La inclusión de un binding en el scope no presupone que una fuente contenga evidencia suficiente para ese campo. La inspección del snapshot determina el scope efectivo.

## 5. Gate de entrada a revisión humana

La autorización ya está cerrada. Ningún candidato puede pasar todavía a `READY_FOR_INDEPENDENT_REVIEW` hasta que se cumplan simultáneamente:

1. snapshot o representación local inmutable con SHA-256 real;
2. inspección de la fuente para fijar bindings bajo revisión y selectores reproducibles;
3. asignación de dos catalogadores distintos;
4. ausencia de secretos o datos no autorizados en los artefactos persistidos;
5. para el candidato 001, verificación de condiciones de reutilización antes de persistir contenido fuente en el repositorio.

Hasta entonces, el conjunto permanece fuera de los denominadores semánticos empíricos y no puede contribuir a un cierre de Gate D.

## 6. Qué no hace este artefacto

No crea adjudicaciones, no inventa hashes ni revisores, no autoriza data egress, no activa proveedores LLM, no crea candidatos runtime, no convierte ninguna evidencia en `VERIFICADO` y no escribe en DSpace.
