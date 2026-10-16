# Torneo de modelos

Plantilla: `ml/__MODELO__/tournament/{modelos,metricas,torneo}.py`. Por defecto: regresión logística, Random Forest,
XGBoost y LightGBM, cada uno **con y sin** un grupo de variables sospechosas (8 candidatos). Si el usuario pide otros
algoritmos o menos, ajusta `candidatos()`; mantén el mismo método para todos.

## Protocolo (sin variable temporal)

1. **Fase 1 — Selección.** Validación cruzada **anidada** sobre train: folds externos (5) para estimar y, dentro de cada uno,
   una búsqueda aleatoria de hiperparámetros con folds internos (3) que optimiza PR-AUC. Cada fold externo se evalúa con
   datos que la búsqueda no vio: la estimación no está inflada por haber elegido el máximo. El campeón es el de mayor
   PR-AUC media en los folds externos.
2. **Fase 2 — Confirmación.** Cada candidato se reajusta con todo train (búsqueda con 5 folds) y se evalúa **una vez** en
   test. Test no interviene en ninguna decisión.

Si hay variable temporal, sustituye los folds por una partición temporal (ventanas crecientes) y deja un periodo de
maduración de etiquetas entre entrenamiento y validación.

## Métricas (`metricas.py`)

PR-AUC (principal), ROC-AUC, F1 máximo, **recall a precisión fija** (80% por defecto) y Brier. La línea base de PR-AUC es la
prevalencia. `make_scorer(..., response_method="predict_proba")` para las personalizadas.

## Búsqueda de hiperparámetros: cómo hacerla y cómo contarla

- Espacios con `scipy.stats` (`loguniform`, `randint`, `uniform`) y listas para categóricos; `random_state` fijo. `n_jobs=1`
  dentro del modelo y paralelismo en la validación (`cross_validate(..., n_jobs=folds)`).
- Prueba el peso de la clase positiva (`scale_pos_weight` = razón negativos:positivos) como hiperparámetro, no como supuesto.
- **Honestidad:** (1) compara el campeón con el **mismo modelo con hiperparámetros por defecto** en los mismos folds: la
  búsqueda suele aportar poco y hay que decirlo; (2) con semilla fija, cada fold muestrea las **mismas** configuraciones, así
  que «4 de 5 folds eligen la misma» no prueba robustez; (3) si los presupuestos (nº de configuraciones) difieren entre
  modelos, dilo en vez de hablar de «mismo criterio»; (4) sin parada temprana, `n_estimators` y `learning_rate` se buscan juntos.

## Lectura de resultados

- Compara **diferencias pareadas por fold** cuando dos modelos empatan: cuántos folds gana uno y la desviación de la
  diferencia, frente a la variación entre folds. Una ventaja menor que esa variación no debe sobrevalorarse.
- Mide cuánto aporta cada variante (con vs sin el grupo sospechoso) y repórtalo: puede ser lo más importante del informe.
- Coherencia validación-test: si el orden de los modelos coincide y las cifras son parecidas, no hay sobreajuste de la selección.
- Guarda `torneo.json` (por fold, hiperparámetros, métricas) y `torneo.md` (tablas) en `tournament/resultados/` (se
  versionan) y el campeón en `artefactos/` (no se versiona).

## Ejecución

```bash
python -m ml.<modelo>.tournament.torneo --rapido   # prueba de humo (pocos folds e iteraciones), ~40 s
python -m ml.<modelo>.tournament.torneo            # completo; lánzalo en segundo plano y espera a que termine
```

La salida del modo rápido se escribe con sufijo `_rapido` y no sirve para `inference`: borra esos archivos antes de la
corrida completa. Con 14 núcleos y ~13 mil filas, la completa tardó ~7 minutos.

## Trampas

- `class_weight`/`scale_pos_weight` pueden mejorar la métrica de ranking muy poco: no los vendas como solución al desbalance.
- No uses `HistGradientBoosting` ni otros modelos que el usuario no pidió.
- El preprocesador **dentro** del `Pipeline`: si lo ajustas fuera, el torneo filtra información de los folds de validación.
