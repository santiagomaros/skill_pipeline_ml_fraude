# Stage processor

Del mart de dbt a datos listos para modelar. Plantilla: `ml/__MODELO__/processor/procesar.py`.

## Responsabilidades

1. **Cargar el mart** (DuckDB, solo lectura) ordenado por `row_id`.
2. **Particionar** 80/20 estratificado con semilla fija. Debe ser **la misma partición del EDA**: mismo orden de filas, misma
   semilla, mismo `test_size`. Compruébalo comparando los conjuntos de índices (con el desfase de 0/1 de `row_id`).
3. **Definir los preprocesadores sin ajustar**, por familia, y con o sin el grupo de variables sospechosas:
   - **lineal:** mediana + `StandardScaler` para numéricas, cuartiles aprendidos de train para las variables en U
     (`KBinsDiscretizer`), one-hot (`handle_unknown="ignore"`) de categóricas, indicadores sin tocar.
   - **árboles:** valores limpios sin transformar (los NaN los manejan los modelos), one-hot de categóricas y los indicadores.
4. **`main()`**: ajusta con todo train, guarda `particion.json` y los preprocesadores para `inference`.

## Qué es one-hot y por qué aquí

Una categórica de *k* niveles se convierte en *k* columnas 0/1 (una por nivel). Los modelos lineales lo necesitan porque no
pueden usar una etiqueta de texto; los árboles de scikit-learn, XGBoost y LightGBM (sin el modo categórico nativo) también
lo reciben así. Con `handle_unknown="ignore"`, un nivel no visto produce todos los ceros; la capa dbt ya envía los no vistos
a `OTRO`, por lo que esto es una segunda red de seguridad.

## Comprobaciones (puerta de calidad)

```python
# la partición coincide con la del EDA
set(train.row_id) == set(df_eda_train.index + 1)

# el preprocesador aprende solo de train
imp = pre.named_transformers_["num"].named_steps["imputar"]
mediana_aprendida == X_train[col].median()      # y != X_completo[col].median()

# la salida lineal no tiene NaN; la de árboles conserva los NaN que deben conservarse
Z_train.isna().sum().sum() == 0
```

También: nombres de columnas sin caracteres especiales que LightGBM rechaza (`" [ ] { } : , +`); por eso las categorías
con `+` se evitan en los árboles (usan la variable numérica) y sólo van en la familia lineal.

## Decisiones que llegan del EDA

Las listas `FLAGS`, `LINEAL_NUM`, `LINEAL_CAT`, `LINEAL_BINS`, `ARBOLES_NUM` y la variable sospechosa se completan con las
decisiones del EDA (la ficha de variables). Las variables sin asociación con el objetivo simplemente no se listan.
