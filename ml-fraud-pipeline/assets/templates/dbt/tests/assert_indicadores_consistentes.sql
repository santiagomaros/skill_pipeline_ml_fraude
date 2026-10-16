-- Cada indicador debe coincidir con la condición que lo define. Devuelve las filas que FALLAN.
-- TODO: una línea por indicador, p. ej.:  (x_falta = 1) <> (x is null)
select row_id
from {{ ref('mart_features') }}
where 1 = 0
