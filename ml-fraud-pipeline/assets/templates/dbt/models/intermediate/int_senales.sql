{# Señales: centinelas e indicadores. Todo es por fila (sin estado): nada depende de otras filas.
   TODO (decisiones del EDA):
     * valor centinela -> NULL con indicador:   case when x = -1 then null else x end as x,  {{ ind('x = -1') }} as x_neg1
     * faltante informativo -> indicador:        {{ ind('x is null') }} as x_falta
     * variable inflacionada de ceros -> x > 0:  {{ ind('x > 0') }} as x_gt0
#}

select *
from {{ ref('stg_datos') }}
