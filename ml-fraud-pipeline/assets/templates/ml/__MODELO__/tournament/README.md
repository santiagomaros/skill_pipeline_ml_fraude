# tournament

Torneo de modelos (`torneo.py`): regresión logística, Random Forest, XGBoost y LightGBM, cada uno con y sin un grupo de
variables sospechosas (ablación).

1. **Selección:** validación cruzada anidada sobre train (búsqueda aleatoria de hiperparámetros optimizando PR-AUC).
2. **Confirmación:** cada candidato se reajusta con todo train y se evalúa una sola vez en test.

```bash
python -m ml.__MODELO__.tournament.torneo --rapido   # prueba de humo
python -m ml.__MODELO__.tournament.torneo            # completo
```

Resultados en `resultados/torneo.md` y `resultados/torneo.json`; el campeón en `artefactos/` (no versionado).
