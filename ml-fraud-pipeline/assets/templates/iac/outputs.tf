output "buckets" {
  description = "Nombre de cada bucket (datos, modelos, resultados)."
  value       = { for k, b in aws_s3_bucket.this : k => b.bucket }
}

output "rol_sagemaker_arn" {
  description = "Rol con el que corren los jobs de SageMaker."
  value       = aws_iam_role.sagemaker.arn
}

output "grupo_registro_modelos" {
  description = "Grupo del registro de modelos de SageMaker."
  value       = aws_sagemaker_model_package_group.fraude.model_package_group_name
}

output "base_datos_glue" {
  description = "Base de datos del catálogo de Glue con las features."
  value       = aws_glue_catalog_database.features.name
}

output "crawler_glue" {
  value = aws_glue_crawler.features.name
}

output "instancia_jobs_ml" {
  description = "Tipo de instancia que usa el DAG para los jobs de SageMaker."
  value       = var.instancia_jobs_ml
}

output "endpoint_fraude" {
  description = "Endpoint en tiempo real (null si crear_endpoint = false)."
  value       = one(aws_sagemaker_endpoint.fraude[*].name)
}

output "ec2_airflow_id" {
  description = "EC2 de Airflow (null si crear_ec2_airflow = false)."
  value       = one(aws_instance.airflow[*].id)
}
