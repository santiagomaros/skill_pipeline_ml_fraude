locals {
  prefijo = "${var.project}-${var.environment}"

  tags = {
    Proyecto  = var.project
    Entorno   = var.environment
    Owner     = var.owner
    ManagedBy = "terraform"
  }

  # Un bucket por propósito. `expira` = null: nunca se borra la versión vigente (modelos y metadatos).
  buckets = {
    datos = {
      descripcion = "Datos crudos y tablas de features (salida de dbt)"
      expira      = var.dias_expirar
    }
    modelos = {
      descripcion = "Modelos, preprocesadores y metadatos de cada versión (métricas, partición, hiperparámetros)"
      expira      = null
    }
    resultados = {
      descripcion = "Scores y recomendaciones generados por inference y recommended"
      expira      = var.dias_expirar
    }
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.buckets

  bucket = "${local.prefijo}-${each.key}-${data.aws_caller_identity.actual.account_id}"
  tags   = { Proposito = each.value.descripcion }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = local.buckets

  bucket                  = aws_s3_bucket.this[each.key].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versionado: permite volver a un modelo o a un resultado anterior.
resource "aws_s3_bucket_versioning" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  # Depende del versionado: las reglas de versiones antiguas lo requieren.
  depends_on = [aws_s3_bucket_versioning.this]

  rule {
    id     = "temperatura-y-expiracion"
    status = "Enabled"

    filter {}

    transition {
      days          = var.dias_a_ia
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.dias_a_glacier
      storage_class = "GLACIER"
    }

    dynamic "expiration" {
      for_each = each.value.expira == null ? [] : [each.value.expira]

      content {
        days = expiration.value
      }
    }

    noncurrent_version_expiration {
      noncurrent_days = var.dias_expirar_versiones
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
