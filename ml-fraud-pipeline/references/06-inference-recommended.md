# Inference y recommended

## inference (`ml/__MODELO__/inference/inferir.py`)

- Carga el **Pipeline completo** (preprocesador + modelo): aplica lo aprendido en train y no recalcula nada.
- **Valida el esquema** antes de puntuar (`feature_names_in_`): falla si faltan columnas, lo que protege contra cambios en
  el mart de dbt.
- Guarda `scores_fraude` (`row_id`, `score` = probabilidad, `particion`, `modelo_version`, `fecha_scoring`). La versión es un
  hash corto del archivo del modelo: cada score sabe con qué versión se generó.
- **Control de consistencia:** el PR-AUC en test debe coincidir con el del torneo (`assert abs(...) < 1e-6`). Si no coincide,
  el modelo guardado no es el que se evaluó, o el preprocesamiento difiere.
- Producción: en lote (Processing job / batch) o en tiempo real (endpoint). El mismo Pipeline sirve para ambos; en tiempo
  real, añade latencia, fallbacks y registro de la versión.

## recommended (`ml/__MODELO__/recommended/recomendar.py`)

Convierte el score en una **acción** por operación y en **motivos**.

### Política por bandas

`aprobar < autenticación adicional (3DS/OTP) < revisión manual < rechazar`. Cada umbral se fija con una **precisión acumulada
objetivo** (p. ej. 90% rechazar, 70% revisión, 50% autenticación): «todo lo que cae en esta banda o por encima es fraude al
menos el X% de las veces».

- Los umbrales se calculan con **predicciones fuera de muestra** (`cross_val_predict`, 5 folds) sobre train. **Nunca** con
  test ni con scores en muestra (inflados).
- Test solo **evalúa** la política: comprueba que la precisión real en test se acerca a la objetivo (confirma que los
  umbrales no están ajustados a test) y reporta por acción: operaciones, tasa del objetivo, % del fraude capturado y % del
  monto de fraude. «Aprobar» es el **riesgo residual**.
- **No inventes costos de negocio.** Con costos reales, la regla de decisión es rechazar si
  `p > C_fp / (monto · L + C_fp)` (el umbral depende del monto); con tres zonas si hay fricción. Déjalo como siguiente paso.
- Las precisiones y volúmenes dependen de la prevalencia de la muestra: en producción se recalibran con la prevalencia real
  y la capacidad de revisión manual.

### Motivos y calibración

- **Motivos por operación:** las 3 variables que más elevan el riesgo, con contribuciones exactas en log-odds para LightGBM
  (`pred_contrib=True`), XGBoost (`pred_contribs=True`) y regresión logística (coeficiente × valor estandarizado); para
  Random Forest la plantilla recurre a `feature_importances_` globales y deja los motivos vacíos (usar un boosting o añadir
  `shap`). Comprueba que `sigmoide(suma de contribuciones + sesgo) == probabilidad`.
- **Calibración:** mira la probabilidad media por decil frente a la tasa observada (en test). Si se desvía, calibra
  (isotónica o Platt) con predicciones fuera de muestra antes de fijar umbrales sobre la probabilidad.

### Informe de recomendaciones (`resultados/recomendaciones.md`)

Política (umbral, precisión objetivo, precisión real en test), resultado por acción, variables más influyentes, resumen por
segmento y 4 recomendaciones. Redacta las recomendaciones a partir de los números (p. ej., cuántas de las 10 variables
más influyentes son categorías del segmento sospechoso) y no con frases fijas: un texto que afirma «la variable X es la
que más pesa» debe verificarse contra la tabla.

## Errores que ya se corrigieron en este stage

- Un texto fijo afirmaba que una variable de segmento era «la que más pesa» y la tabla mostraba otra: las frases del informe
  se generan a partir de los números (p. ej., cuántas de las 10 variables más influyentes son categorías del segmento).
- Los conteos por segmento salían como decimales al iterar con `iterrows`: conviértelos a entero al imprimir.
