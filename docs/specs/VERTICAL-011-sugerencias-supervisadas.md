# Vertical 011: sugerencias supervisadas

El endpoint `GET /api/items/{uuid}/suggestions` propone valores únicamente para
campos lingüísticos ausentes. Usa vecinos estructuralmente similares, exige al
menos dos registros soporte y un consenso mínimo de 75 %, y devuelve valor,
confianza, explicación y UUID de la evidencia.

La ficha permite copiar una propuesta al editor del navegador. Copiar no guarda
un borrador, no registra una aceptación y no modifica DSpace. El catalogador debe
revisar la evidencia, justificar su decisión y guardar explícitamente el borrador
local. Si no hay evidencia suficiente, la respuesta contiene una lista vacía.

Esta primera versión es determinista y no depende de un proveedor de modelos,
embeddings ni vocabularios inventados.
