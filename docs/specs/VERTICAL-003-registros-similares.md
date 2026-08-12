# VERTICAL-003: Registros similares con evidencia estructurada

## Objetivo

Recuperar vecinos de un ítem dentro de su colección y explicar cada coincidencia sin embeddings ni modelo generativo.

## Método inicial

- Coincidencia normalizada por valor en los cuatro campos lingüísticos.
- Solapamiento de al menos dos tokens de título.
- Puntaje de ordenamiento ponderado; no representa confianza ni probabilidad.
- Máximo de 20 resultados por solicitud y 2,000 candidatos evaluados.

## Evidencia

Cada resultado incluye el campo, valores o tokens coincidentes y su contribución al puntaje. La clave `dc.subject.linguiscgroup` se conserva literalmente.

## Límites

- Sólo se comparan ítems activos de la misma colección.
- No se usan bitstreams, fuentes externas, vocabularios inferidos ni embeddings.
- Si la colección supera el límite interno, la respuesta indica `truncated=true`.
- La recuperación no genera ni aplica sugerencias.

## Aceptación

1. La fuente nunca aparece entre sus propios vecinos.
2. La misma entrada produce el mismo orden y evidencia.
3. Los vecinos sin evidencia quedan excluidos.
4. El límite se aplica después de ordenar por puntaje.
5. API y web distinguen el puntaje de una confianza catalográfica.
6. Un fallo de recuperación no impide consultar la ficha sincronizada.
