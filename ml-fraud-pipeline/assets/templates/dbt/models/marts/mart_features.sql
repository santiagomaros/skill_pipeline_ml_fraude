{# Mart de features: una fila por operación, listo para el `processor` (ml/__MODELO__/processor).
   Contrato: solo transformaciones SIN ESTADO y con parámetros fijos (ver vars en dbt_project.yml).
   Lo que se aprende de los datos (medianas, cuartiles, codificadores, escalado) y la partición train/test
   NO van aquí: los ajusta el `processor` solo con train.
   TODO: agrupaciones con parámetros fijos (case when ... in (...)), topes (least(x, {{ var('tope_x') }})) y log1p (ln(1 + x)). #}

select *
from {{ ref('int_senales') }}
