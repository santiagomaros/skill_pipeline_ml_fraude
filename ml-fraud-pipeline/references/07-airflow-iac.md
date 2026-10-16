# Airflow e IaC

## DAG diario (`airflow/dags/<proyecto>_diario.py`)

```
dbt_build ─► publicar_features_s3 ─► crawler_glue ─► processor ─► ¿día de torneo? ─┬─► torneo ───────┐
                                                                                   └─► omitir_torneo ┤
                                                                       inference ◄─────────────────┘
                                                                           └─► recommended ─► fin
```

- **`dbt build`** (modelos + pruebas) abre el flujo: si una prueba falla no corre nada más (no se puntúa con datos malos).
- **Reentrenamiento semanal:** `BranchPythonOperator` elige `torneo` (p. ej. los lunes) u `omitir_torneo`; `inference`
  lleva `trigger_rule="none_failed_min_one_success"` para correr tras cualquiera de las dos ramas.
- **Jobs de ML como SageMaker Processing jobs** (`SageMakerProcessingOperator`): una configuración común
  (`trabajo_ml(id, modulo, entradas, salidas)`) con imagen del proyecto, rol, tipo de instancia, `StoppingCondition` y
  entradas/salidas en S3. SageMaker crea y destruye las máquinas en cada ejecución: no hace falta un clúster permanente.
- Parámetros (buckets, rol, imagen, crawler, tipo de instancia, target de dbt) como **Variables de Airflow** con valores de
  referencia por defecto, para que el DAG siempre se pueda parsear; se cargan desde las salidas de Terraform.
- `catchup=False`, `max_active_runs=1`, reintentos con espera, etiquetas.

### Verificación sin Airflow (`airflow/tests/verificar_dag.py`)

Sustituye `airflow` por clases mínimas que registran tareas y dependencias, importa el DAG y comprueba el grafo, la regla de
ejecución, la configuración de los jobs y la rama de día de torneo. **Es una prueba de estructura, no de ejecución:**
declara que el DAG no se corrió en un Airflow real. Airflow puede no soportar la versión de Python del proyecto; no lo
instales a la fuerza.

**Adaptación pendiente a nivel de código:** los módulos de `ml/` leen archivos locales (DuckDB); para correr en SageMaker se
cambian por las rutas montadas desde S3 (`/opt/ml/processing/...`). Dilo en el README.

## Terraform (`iac/`)

| Archivo | Contenido |
|---|---|
| `s3.tf` | 3 buckets (datos, modelos con metadatos, resultados): versionado, cifrado AES256, acceso público bloqueado, ciclo de vida (STANDARD_IA → GLACIER → expiración; **los modelos no expiran**, solo sus versiones antiguas) |
| `iam.tf` | Roles de mínimo privilegio: SageMaker (S3 del proyecto, logs, ECR), Glue (lee las features) y Airflow (lanza jobs, `iam:PassRole` solo del rol de SageMaker, arranca el crawler) |
| `glue.tf` | Base de datos del catálogo y crawler diario sobre las features |
| `sagemaker.tf` | Grupo del **registro de modelos** (versiones con su metadato), grupo de logs y, **opcional**, endpoint serverless |
| `ec2.tf` | **Opcional**: EC2 para Airflow (IMDSv2, disco cifrado, sin acceso entrante salvo los CIDR indicados) |
| `outputs.tf` / `variables.tf` | Salidas (para las Variables de Airflow) y parámetros con validaciones |

- Los recursos que **cuestan** (`crear_endpoint`, `crear_ec2_airflow`) están en `false` por defecto.
- Valida con `terraform fmt -recursive`, `terraform init -backend=false` y `terraform validate`. Sin credenciales no se puede
  hacer `plan` ni `apply`: **no lo afirmes**. Versiona `.terraform.lock.hcl`; no versiones `*.tfstate` ni `*.tfvars`.
- Estado remoto (S3 + bloqueo en DynamoDB) en `versions.tf`, comentado como referencia.
- Para GCP: sustituye por BigQuery/Vertex AI/Cloud Composer manteniendo la misma separación de responsabilidades.

## Trampas

- Las reglas de `lifecycle` con versiones antiguas necesitan el versionado activo (`depends_on`).
- Un `precondition` en la EC2 evita crearla sin `subnet_id`.
- Las políticas con `resources = ["*"]` en SageMaker son una concesión para la simulación; en un despliegue real se acotan.
