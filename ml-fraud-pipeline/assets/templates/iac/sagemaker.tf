# Registro de modelos: cada versión del campeón se registra aquí con su metadato (métricas, partición, hiperparámetros).
resource "aws_sagemaker_model_package_group" "fraude" {
  model_package_group_name        = "${local.prefijo}-modelo"
  model_package_group_description = "Versiones del modelo (LightGBM) y sus metadatos"
}

resource "aws_cloudwatch_log_group" "ml" {
  name              = "/aws/sagemaker/${local.prefijo}"
  retention_in_days = 30
}

# Los jobs de procesamiento (processor, tournament, inference, recommended) no necesitan un clúster permanente:
# Airflow los lanza con `instancia_jobs_ml` y SageMaker crea y destruye las máquinas en cada ejecución.

# ---- Inferencia en tiempo real (opcional): endpoint serverless, se paga solo por uso ----
resource "aws_sagemaker_model" "fraude" {
  count = var.crear_endpoint ? 1 : 0

  name               = "${local.prefijo}-fraude"
  execution_role_arn = aws_iam_role.sagemaker.arn

  primary_container {
    image          = var.imagen_ml
    model_data_url = "s3://${aws_s3_bucket.this["modelos"].bucket}/campeon/model.tar.gz"
  }
}

resource "aws_sagemaker_endpoint_configuration" "fraude" {
  count = var.crear_endpoint ? 1 : 0

  name = "${local.prefijo}-fraude"

  production_variants {
    variant_name = "AllTraffic"
    model_name   = aws_sagemaker_model.fraude[0].name

    serverless_config {
      max_concurrency   = 5
      memory_size_in_mb = 2048
    }
  }
}

resource "aws_sagemaker_endpoint" "fraude" {
  count = var.crear_endpoint ? 1 : 0

  name                 = "${local.prefijo}-fraude"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.fraude[0].name
}
