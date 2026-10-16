# __PROYECTO__

Detección de fraude en transacciones: dbt (features sin estado) → processor → torneo → inference → recommended,
orquestado con Airflow sobre AWS (Terraform).

## Estructura

```
dbt/        capa SQL de features (stg → int → mart) con pruebas
ml/__MODELO__/
  processor/    partición y preprocesadores que aprenden de train
  tournament/   validación cruzada anidada y selección del modelo
  inference/    scores con el modelo campeón
  recommended/  acciones de prevención y motivos
airflow/    DAG diario
iac/        Terraform (S3, IAM, Glue, SageMaker, EC2)
src/eda/    análisis exploratorio
reports/    informe y figuras
```

## Cómo ejecutarlo

```bash
cd dbt && dbt build --profiles-dir .            # features + pruebas
python -m ml.__MODELO__.processor.procesar      # partición y preprocesadores
python -m ml.__MODELO__.tournament.torneo       # torneo (usa --rapido para una prueba de humo)
python -m ml.__MODELO__.inference.inferir       # scores
python -m ml.__MODELO__.recommended.recomendar  # recomendaciones
```
