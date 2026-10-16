# recommended

Convierte los scores en acciones de prevención (`recomendar.py`): aprobar, autenticación adicional, revisión manual o
rechazar, con umbrales de precisión acumulada objetivo calculados con predicciones fuera de muestra de train, y los
motivos por operación. Salida: tabla `recomendaciones` y `resultados/recomendaciones.md`.

```bash
python -m ml.__MODELO__.recommended.recomendar
```

Las precisiones y los volúmenes dependen de la prevalencia de la muestra: en producción se recalibran.
