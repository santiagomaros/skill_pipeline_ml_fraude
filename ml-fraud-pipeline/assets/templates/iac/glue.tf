# Catálogo de datos para consultar las features con Athena (el mismo SQL de dbt apunta aquí en producción).
resource "aws_glue_catalog_database" "features" {
  name        = replace("${local.prefijo}_features", "-", "_")
  description = "Tablas de features del modelo"
}

resource "aws_glue_crawler" "features" {
  name          = "${local.prefijo}-features"
  database_name = aws_glue_catalog_database.features.name
  role          = aws_iam_role.glue.arn
  schedule      = var.cron_crawler

  s3_target {
    path = "s3://${aws_s3_bucket.this["datos"].bucket}/features/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}
