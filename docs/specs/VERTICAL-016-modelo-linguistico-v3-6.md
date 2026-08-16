# VERTICAL-016: Modelo lingüístico alineado con dspace-cataloger v3.6

## Resultado observable

La aplicación permite revisar y preparar borradores locales para cinco campos lingüísticos, incluido `dc.subject.linguisticVariant`, sin modificar DSpace. El perfil de colección muestra la variante como dimensión independiente y deja de representar la lengua de registro como descendiente de la agrupación estudiada.

## Contrato de campos

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticVariant`
- `dc.description.registeredLanguage`

`dc.subject.linguiscgroup` se conserva literalmente.

## Semántica

Para recursos sobre lenguas indígenas de México:

**Familia → Agrupación → Variante** corresponde al eje normativo CLIN/INALI.

`Rama` es un enriquecimiento genealógico opcional. `Lengua de registro` es la lengua de redacción/registro del recurso y constituye un eje independiente.

La aplicación no reconstruye todavía relaciones uno-a-uno entre valores repetibles de esos campos. Las relaciones del perfil son observaciones agregadas del corpus y nunca equivalen a una autoridad institucional.

## Diagnósticos

- Familia sin rama: válido; no genera hallazgo.
- Rama sin familia: `CAT-LING-002` error.
- Agrupación sin familia: `CAT-LING-004` warning.
- Variante sin agrupación: `CAT-LING-005` warning.
- Duplicados normalizados en cualquiera de los cinco campos: `CAT-LING-003` warning.
- Valor fuera de un vocabulario activo aprobado: `CAT-VOCAB-001` warning.

## Vocabularios

La variante puede tener una revisión local aprobada y validación literal. No se presupone un endpoint DSpace de promoción para variantes; si no existe una lista DSpace mapeada, la carga de autoridad se realiza manualmente mediante la gobernanza local existente.

## Sugerencias

La variante **no** se incorpora todavía a las sugerencias por consenso entre vecinos. Puede editarse manualmente y validarse, pero cualquier mecanismo de recomendación de variantes requiere una vertical posterior con autoridad explícita.

## Criterios de aceptación

1. El editor muestra cinco campos.
2. La API acepta `dc.subject.linguisticVariant` en borradores.
3. La validación admite una revisión local para `dc.subject.linguisticVariant`.
4. El perfil contabiliza cobertura y valores de variante.
5. `registeredLanguage` no forma parte de `RELATIONSHIP_SPECS` con agrupación.
6. Familia sin rama no genera hallazgo.
7. Variante sin agrupación genera `CAT-LING-005`.
8. No existe escritura en DSpace.
