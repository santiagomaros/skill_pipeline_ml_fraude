# inference

Puntúa operaciones con el modelo campeón (`inferir.py`) y guarda `scores_fraude` (`row_id`, `score`, `particion`,
`modelo_version`, `fecha_scoring`). Valida el esquema de entrada y comprueba que reproduce la métrica de test del torneo.

```bash
python -m ml.__MODELO__.inference.inferir
```
