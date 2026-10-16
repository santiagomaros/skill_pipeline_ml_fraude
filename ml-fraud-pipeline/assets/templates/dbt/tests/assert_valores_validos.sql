-- Falla si algún valor rompe lo observado en el EDA (rangos, signos, proporciones en [0, 1], importes > 0).
-- TODO: reemplazar la condición por las reglas reales del dataset. Debe devolver las filas que FALLAN.
select row_id
from {{ ref('stg_datos') }}
where 1 = 0
