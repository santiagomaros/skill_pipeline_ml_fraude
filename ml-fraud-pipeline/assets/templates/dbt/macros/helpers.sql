{# Convierte texto a número: quita la coma de miles, trata vacío como NULL y no falla si no es numérico. #}
{% macro parse_num(columna, tipo) %}
    {{ dbt.safe_cast("nullif(replace(trim(" ~ columna ~ "), ',', ''), '')", tipo) }}
{% endmacro %}

{# Indicador 0/1 a partir de una condición (portable entre motores). #}
{% macro ind(condicion) %}
    case when {{ condicion }} then 1 else 0 end
{% endmacro %}

{# Decimal de doble precisión. dbt.type_float() es FLOAT de 32 bits en DuckDB y distorsiona montos (12538.44 -> 12538.4404). #}
{% macro tipo_decimal() %}
    {{ return(adapter.dispatch('tipo_decimal', '__PROYECTO_SNAKE__')()) }}
{% endmacro %}

{% macro default__tipo_decimal() %}double precision{% endmacro %}
{% macro bigquery__tipo_decimal() %}float64{% endmacro %}
{% macro athena__tipo_decimal() %}double{% endmacro %}
