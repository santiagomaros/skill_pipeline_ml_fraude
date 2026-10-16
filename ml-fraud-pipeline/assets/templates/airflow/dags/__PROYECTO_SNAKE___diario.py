"""DAG diario del modelo de fraude: encadena dbt, processor, torneo (semanal), inference y recommended.

  dbt_build ─► publicar_features_s3 ─► crawler_glue ─► processor ─► ¿lunes? ─┬─► torneo ───────┐
                                                                             └─► omitir_torneo ┤
                                                                   inference ◄─────────────────┘
                                                                       └─► recommended ─► fin

 * Si una prueba de dbt falla, `dbt build` falla y no corre nada más (no se puntúa con datos malos).
 * El torneo (reentrenamiento) corre solo los lunes; el resto de los días se usa el campeón vigente.
 * Los jobs de ML son SageMaker Processing jobs: SageMaker crea y destruye las máquinas en cada ejecución.

Simulación: el DAG se verificó con `airflow/tests/verificar_dag.py` (estructura y dependencias), no en un Airflow real.
Los nombres de buckets, el rol y la imagen salen de las salidas de Terraform (iac/), cargadas como Variables de Airflow.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator
from airflow.providers.amazon.aws.operators.sagemaker import SageMakerProcessingOperator

# --- Parámetros (Variables de Airflow, con valores de referencia para que el DAG siempre se pueda leer) ---
BUCKET_DATOS = Variable.get("__PROYECTO_SNAKE___bucket_datos", default_var="__PROYECTO__-dev-datos")
BUCKET_MODELOS = Variable.get("__PROYECTO_SNAKE___bucket_modelos", default_var="__PROYECTO__-dev-modelos")
BUCKET_RESULTADOS = Variable.get("__PROYECTO_SNAKE___bucket_resultados", default_var="__PROYECTO__-dev-resultados")
ROL_SAGEMAKER = Variable.get("__PROYECTO_SNAKE___rol_sagemaker", default_var="arn:aws:iam::123456789012:role/__PROYECTO__-dev-sagemaker")
IMAGEN_ML = Variable.get("__PROYECTO_SNAKE___imagen_ml", default_var="123456789012.dkr.ecr.us-east-1.amazonaws.com/__PROYECTO__-ml:latest")
INSTANCIA = Variable.get("__PROYECTO_SNAKE___instancia_jobs_ml", default_var="ml.m5.xlarge")
CRAWLER = Variable.get("__PROYECTO_SNAKE___crawler_glue", default_var="__PROYECTO__-dev-features")
DBT_TARGET = Variable.get("__PROYECTO_SNAKE___dbt_target", default_var="prod")

DIA_DE_TORNEO = 0   # lunes (datetime.weekday())


def _entrada(nombre: str, bucket: str, prefijo: str) -> dict:
    return {"InputName": nombre, "S3Input": {"S3Uri": f"s3://{bucket}/{prefijo}", "LocalPath": f"/opt/ml/processing/input/{nombre}",
                                              "S3DataType": "S3Prefix", "S3InputMode": "File"}}


def _salida(nombre: str, bucket: str, prefijo: str) -> dict:
    return {"OutputName": nombre, "S3Output": {"S3Uri": f"s3://{bucket}/{prefijo}", "LocalPath": f"/opt/ml/processing/output/{nombre}",
                                                "S3UploadMode": "EndOfJob"}}


def trabajo_ml(id_tarea: str, modulo: str, entradas: list[dict], salidas: list[dict], horas: int = 1) -> SageMakerProcessingOperator:
    """SageMaker Processing job que ejecuta un módulo de ml/modelo___PROYECTO_SNAKE__ dentro de la imagen del proyecto."""
    config = {
        "ProcessingJobName": f"__PROYECTO__-{id_tarea}-{{{{ ts_nodash }}}}",
        "RoleArn": ROL_SAGEMAKER,
        "AppSpecification": {"ImageUri": IMAGEN_ML, "ContainerEntrypoint": ["python", "-m", modulo]},
        "ProcessingResources": {"ClusterConfig": {"InstanceCount": 1, "InstanceType": INSTANCIA, "VolumeSizeInGB": 30}},
        "StoppingCondition": {"MaxRuntimeInSeconds": horas * 3600},
        "ProcessingInputs": entradas,
        "ProcessingOutputConfig": {"Outputs": salidas},
        "Environment": {"MART_DUCKDB": "/opt/ml/processing/input/features/fraude.duckdb"},
    }
    return SageMakerProcessingOperator(task_id=id_tarea, config=config, aws_conn_id="aws_default", wait_for_completion=True)


def elegir_rama(logical_date, **_) -> str:
    """Los lunes se reentrena (torneo); el resto de los días se usa el campeón vigente."""
    return "torneo" if logical_date.weekday() == DIA_DE_TORNEO else "omitir_torneo"


with DAG(
    dag_id="__PROYECTO_SNAKE___diario",
    description="Features con dbt, torneo semanal, scoring diario y recomendaciones de prevención de fraude",
    schedule="0 6 * * *",                       # todos los días a las 06:00 UTC
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "equipo-ml", "retries": 1, "retry_delay": timedelta(minutes=10)},
    tags=["fraude", "ml", "dbt", "sagemaker"],
) as dag:

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd /opt/airflow/dbt && dbt build --profiles-dir . --target " + DBT_TARGET,   # modelos + pruebas
    )

    publicar_features = BashOperator(
        task_id="publicar_features_s3",
        bash_command=f"aws s3 sync /opt/airflow/dbt/target/features s3://{BUCKET_DATOS}/features/ --delete",
    )

    crawler = GlueCrawlerOperator(task_id="crawler_glue", config={"Name": CRAWLER}, wait_for_completion=True)

    processor = trabajo_ml(
        "processor", "ml.__MODELO__.processor.procesar",
        entradas=[_entrada("features", BUCKET_DATOS, "features/")],
        salidas=[_salida("artefactos", BUCKET_MODELOS, "preprocesadores/")],
    )

    rama = BranchPythonOperator(task_id="es_dia_de_torneo", python_callable=elegir_rama)

    torneo = trabajo_ml(
        "torneo", "ml.__MODELO__.tournament.torneo",
        entradas=[_entrada("features", BUCKET_DATOS, "features/")],
        salidas=[_salida("modelo_y_metadatos", BUCKET_MODELOS, "campeon/")],
        horas=3,
    )
    omitir_torneo = EmptyOperator(task_id="omitir_torneo")

    inference = trabajo_ml(
        "inference", "ml.__MODELO__.inference.inferir",
        entradas=[_entrada("features", BUCKET_DATOS, "features/"), _entrada("modelo", BUCKET_MODELOS, "campeon/")],
        salidas=[_salida("scores", BUCKET_RESULTADOS, "scores/")],
    )
    inference.trigger_rule = "none_failed_min_one_success"       # corre tras el torneo o tras omitirlo

    recomendaciones = trabajo_ml(
        "recommended", "ml.__MODELO__.recommended.recomendar",
        entradas=[_entrada("scores", BUCKET_RESULTADOS, "scores/"), _entrada("modelo", BUCKET_MODELOS, "campeon/")],
        salidas=[_salida("recomendaciones", BUCKET_RESULTADOS, "recomendaciones/")],
    )

    fin = EmptyOperator(task_id="fin")

    dbt_build >> publicar_features >> crawler >> processor >> rama
    rama >> [torneo, omitir_torneo] >> inference >> recomendaciones >> fin
