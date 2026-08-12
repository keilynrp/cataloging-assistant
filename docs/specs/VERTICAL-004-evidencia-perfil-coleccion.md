# VERTICAL-004: Evidencia del perfil de colección

## Objetivo

Mostrar métricas reconciliadas del índice local para decidir campos obligatorios y relaciones lingüísticas con evidencia, sin declarar reglas institucionales.

## Fuente y grano

- Fuente: PostgreSQL operacional, derivado de la última sincronización DSpace.
- Población: ítems activos de la colección piloto.
- Grano base: un ítem; los valores repetibles conservan su multiplicidad.
- Valor presente: existe al menos un valor no vacío para el campo.

## Métricas

- Cobertura: ítems con campo / ítems activos.
- Ausencia: ítems activos menos ítems con campo.
- Volumen: valores no vacíos, incluidos los repetibles.
- Distintos: valores textuales distintos observados.
- Completitud: combinación de los cuatro campos presentes por ítem.
- Relación observada: ítems distintos que contienen ambos valores del par.

## Visuales

- Tarjetas y barras horizontales para comparar cobertura.
- Barras clasificadas para los seis valores más frecuentes por campo.
- Lista de patrones de completitud con denominador visible.
- Tabla de relaciones para consulta exacta.

## Límites

- Las frecuencias históricas no autorizan vocabularios ni relaciones.
- No se infiere obligatoriedad, preferencia ortográfica ni causalidad.
- Se muestran hasta 10 valores por campo y 25 pares por relación en el contrato.
- La vista es una fotografía en vivo del índice local, no un reporte histórico.

## Aceptación

1. Todos los porcentajes usan el mismo denominador de ítems activos.
2. Los patrones de completitud suman el total de ítems activos.
3. Los valores vacíos no cuentan como presencia.
4. Los valores repetibles incrementan volumen sin duplicar cobertura del ítem.
5. La frescura y el origen son visibles.
6. La UI advierte que las relaciones son observadas, no controladas.
7. La suite automatizada no consulta DSpace real.
