# processor

Del mart de dbt a datos listos para modelar (`procesar.py`).

- Lee el mart (DuckDB) y parte train/test: 80/20 estratificado con semilla fija (la misma partición del EDA).
- Define preprocesadores que aprenden de train: `lineal` y `arboles`, con y sin el grupo de variables sospechosas.
- Se ajustan solo con train; en validación cruzada van dentro del `Pipeline` y se reajustan en cada fold.

```bash
python -m ml.__MODELO__.processor.procesar
```
