{{ config(severity='warn') }}
-- Guardia de volumen/deriva: avisa si la tasa del objetivo sale del rango esperado.
-- TODO: reemplazar `objetivo` por la columna objetivo del mart.
select round(avg({{ dbt.safe_cast('objetivo', tipo_decimal()) }}), 4) as tasa_objetivo
from {{ ref('mart_features') }}
having avg({{ dbt.safe_cast('objetivo', tipo_decimal()) }}) < {{ var('tasa_objetivo_min') }}
    or avg({{ dbt.safe_cast('objetivo', tipo_decimal()) }}) > {{ var('tasa_objetivo_max') }}
