# Capa dbt: features sin estado

## Capas

```
source raw.datos ─► stg_datos ─► int_senales ─► mart_features
   (CSV, texto)      tipado y      centinelas e      features sin estado
                     limpieza      indicadores       (contrato con el processor)
```

- **staging:** tipado y limpieza. Con DuckDB el CSV se lee como texto (`all_varchar=true`) y se convierte aquí con
  `parse_num(columna, tipo)`: quita la coma de miles y trata el vacío como NULL. `row_id` sigue el orden del archivo si no
  hay identificador.
- **intermediate:** centinelas → NULL con indicador (`x_neg1`), indicador de faltante (`x_falta`), `x_gt0` en variables
  inflacionadas de ceros. Todo por fila.
- **mart:** topes fijos (`least(x, tope)`), categorías (`case`), agrupación con **lista fija** (`j in (...)` → `OTRO`),
  `ln(1 + x)`. Los parámetros viven en `vars` de `dbt_project.yml` y vienen del EDA.

## Qué NO va en dbt

Medianas, cuantiles, desviaciones, frecuencias, target encoding, la etiqueta: cualquier estadística del conjunto completo
(serían fuga hacia test y desfase con inferencia). `verificar_proyecto.py` busca `avg/median/ntile … over ()` en int y marts.

## Desarrollo local con DuckDB

`sources.yml` usa `meta.external_location: "read_csv('<ruta>', header=true, all_varchar=true)"` con la ruta en una variable
de entorno (`DATOS_CSV_PATH`): el CSV no se versiona. En producción la fuente es una tabla del catálogo (Athena/Glue,
BigQuery…) y esa clave se ignora; el SQL de los modelos no cambia, solo el adaptador (`profiles.yml`, con el perfil de
producción documentado y comentado). Ejecuta con `dbt build --profiles-dir .` desde `dbt/` (crea antes `target/`).

## Pruebas (tres niveles)

1. **Genéricas** (`unique`, `not_null`, `accepted_values`): `row_id` único, objetivo en {0, 1}, valores permitidos de cada
   agrupación y tope — son el **contrato** con el processor.
2. **Singulares** (`tests/*.sql`, devuelven las filas que fallan): rangos y signos observados en el EDA, el mart conserva las
   filas del staging, cada indicador coincide con su definición, y una guardia de la tasa del objetivo con
   `severity='warn'`.
3. **Unitarias** (`unit_tests:`): filas construidas a mano para topes, categorías, agrupación y `log1p`.

`dbt build` ejecuta modelos y pruebas en orden de dependencia: si una prueba falla, **los modelos que dependen de ella no se
ejecutan**. En Airflow esto detiene el pipeline antes de puntuar con datos malos.

## Verificaciones obligatorias

- **Paridad con pandas.** Reimplementa en pandas las transformaciones y compara: filas, conteo de cada indicador, sumas de
  columnas numéricas, igualdad de las agrupaciones y de los logaritmos. Esta comparación encontró un defecto real.
- **Prueba negativa.** Genera un CSV con un importe negativo, un centinela inválido y un objetivo fuera de {0, 1}: deben
  fallar las pruebas correspondientes y saltarse los modelos posteriores.

## Trampas conocidas

- **`dbt.type_float()` es FLOAT de 32 bits en DuckDB** y distorsiona importes (`12538.44` → `12538.4404`). Usa la macro
  `tipo_decimal()` (doble precisión; variantes por adaptador con `adapter.dispatch`).
- **El Jinja dentro de un comentario SQL (`--`) se ejecuta.** Un `{{ macro() }}` de ejemplo en un comentario se expande y
  puede romper la consulta; los ejemplos van en comentarios Jinja (llaves con almohadilla). Y un comentario Jinja termina en
  el primer cierre que encuentre: no anides otro dentro.
- **`target/` debe existir** antes del primer `dbt build` con DuckDB en archivo.
- Las columnas en minúsculas (convención SQL); el processor las consume tal cual y el EDA (si usa otros nombres) debe
  mapearlos.
- Comprueba que `dbt` y las versiones de Python/DuckDB son compatibles antes de prometer la ejecución.
