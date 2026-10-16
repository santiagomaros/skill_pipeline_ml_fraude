# Errores comunes (y cómo se detectaron)

Lista de comprobación final. Todos ocurrieron en el desarrollo original.

| # | Error | Cómo aparece | Cómo evitarlo / detectarlo |
|---|---|---|---|
| 1 | `pd.to_numeric(errors='coerce')` convierte en NaN los valores con coma de miles | El máximo de un importe cae de 12.538 a 998 | Leer con `thousands=','`; comprobar que no se crean NaN |
| 2 | Imputar por posición (`bfill`) o partir sin mirar el orden | Archivo ordenado por clase: primeras filas 100% fraude | Revisar la tasa en las primeras filas; no usar posición |
| 3 | Eliminar una columna por tener muchos faltantes | La ausencia de `K` (76%) se asocia con el fraude | χ² faltante↔objetivo; indicador de faltante |
| 4 | Imputar con la media antes de partir | Fuga y media ≫ mediana en variables asimétricas | Mediana de train, dentro del pipeline |
| 5 | Confiar en un test monótono | Variable en U con AUC ≈ 0,5 y χ² muy significativo | Gráfico por tramos + χ²/tendencia por nivel |
| 6 | Conclusiones que citan análisis retirados | Resumen con IV, PSI, LRT que el cuaderno ya no calcula | Revisar conclusiones tras cada recorte |
| 7 | Una celda usa una variable definida más abajo | `NameError` solo en una ejecución limpia | Ejecutar el cuaderno de arriba abajo en kernel limpio |
| 8 | Cortes distintos al comparar train y test (PSI) | PSI = 13,8 | Calcular los cortes en train y aplicarlos a ambos |
| 9 | `dbt.type_float()` en DuckDB | Importes con error de 32 bits | Macro `tipo_decimal()`; paridad con pandas |
| 10 | Jinja dentro de un comentario SQL | `dbt build` falla con error de sintaxis | Comentarios Jinja para los ejemplos; no anidar cierres |
| 11 | Tabla `mart`/`TARGET` distintos entre dbt y `config.py` | El processor no encuentra la tabla | Un solo nombre; `scaffold.py` los alinea |
| 12 | `recommended` asume LightGBM | `predict(pred_contrib=...)` falla con otro campeón | `_contribuciones()` por tipo de modelo + fallback |
| 13 | Salida del modo `--rapido` usada por `inference` | `modelo_campeon_rapido.joblib` no es el esperado | Borrar los `_rapido` antes de la corrida completa |
| 14 | Texto del informe que afirma algo que la tabla contradice | «El país es la variable que más pesa» y era `b` | Contrastar cada afirmación con la tabla |
| 15 | «Mismo criterio de búsqueda» con presupuestos distintos | 10/12/20/20 configuraciones | Decir el número de configuraciones por modelo |
| 16 | Presentar una simulación como despliegue | DAG sin Airflow real, IaC sin `plan` | Declarar qué se verificó y qué no |
| 17 | Numeración de listas que continúa entre secciones | «7., 8.» en la primera lista de otra sección | Una referencia de numeración por lista |
| 18 | Marcas literales en el informe | `**` o `` ` `` visibles | No anidar código dentro de negritas; soportar cursivas |
| 19 | Datos, estados o modelos versionados | `*.csv`, `*.tfstate`, `*.joblib` en Git | `.gitignore` + `verificar_proyecto.py` |
| 20 | Confirmar (commit) cambios del usuario sin permiso | Árbol con borrados y renombrados pendientes | No hacer commit en su nombre; avisar |

## Verificación final

```bash
python scripts/verificar_proyecto.py <ruta>     # estática: estructura, .gitignore, secretos, dbt, ml, DAG, S3
dbt build --profiles-dir .                      # pruebas de datos y unitarias
python airflow/tests/verificar_dag.py           # estructura del DAG
terraform validate                              # IaC (sin plan/apply)
```
