{# Staging: tipado y limpieza, sin lógica de negocio.
   * row_id sigue el orden del archivo (si los datos no traen un identificador).
   * Convertir con parse_num (quita la coma de miles, vacío = NULL) y tipo_decimal() (doble precisión; NO dbt.type_float()).
   * IMPORTANTE: el código Jinja dentro de un comentario SQL con guiones SE EJECUTA; los ejemplos van en comentarios Jinja (este tipo de bloque).
   TODO: reemplazar `select *` por la lista explícita de columnas con su tipo, por ejemplo:
     {{ parse_num('"monto"', tipo_decimal()) }} as monto,
     {{ parse_num('"objetivo"', dbt.type_int()) }} as objetivo,
#}

select row_number() over () as row_id, *
from {{ source('raw', 'datos') }}
