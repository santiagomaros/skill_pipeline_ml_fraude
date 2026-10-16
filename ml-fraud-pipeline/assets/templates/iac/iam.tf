locals {
  arns_buckets = flatten([for b in aws_s3_bucket.this : [b.arn, "${b.arn}/*"]])
}

# ---- Rol de ejecución de los jobs de SageMaker (processor, tournament, inference, recommended) ----
data "aws_iam_policy_document" "confianza_sagemaker" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "permisos_sagemaker" {
  statement {
    sid       = "S3Proyecto"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = local.arns_buckets
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:log-group:/aws/sagemaker/*"]
  }

  statement {
    sid       = "ImagenesEcr"
    actions   = ["ecr:GetAuthorizationToken", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = ["*"]
  }
}

resource "aws_iam_role" "sagemaker" {
  name               = "${local.prefijo}-sagemaker"
  assume_role_policy = data.aws_iam_policy_document.confianza_sagemaker.json
}

resource "aws_iam_role_policy" "sagemaker" {
  name   = "acceso-proyecto"
  role   = aws_iam_role.sagemaker.id
  policy = data.aws_iam_policy_document.permisos_sagemaker.json
}

# ---- Rol del crawler de Glue (lee las features en S3 y actualiza el catálogo) ----
data "aws_iam_policy_document" "confianza_glue" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "permisos_glue" {
  statement {
    sid       = "LeerFeatures"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.this["datos"].arn, "${aws_s3_bucket.this["datos"].arn}/*"]
  }
}

resource "aws_iam_role" "glue" {
  name               = "${local.prefijo}-glue"
  assume_role_policy = data.aws_iam_policy_document.confianza_glue.json
}

resource "aws_iam_role_policy_attachment" "glue_servicio" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue" {
  name   = "leer-features"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.permisos_glue.json
}

# ---- Rol de la EC2 de Airflow: lanza jobs de SageMaker y el crawler, y lee/escribe en los buckets ----
data "aws_iam_policy_document" "confianza_ec2" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "permisos_airflow" {
  statement {
    sid = "JobsSageMaker"
    actions = [
      "sagemaker:CreateProcessingJob", "sagemaker:DescribeProcessingJob", "sagemaker:StopProcessingJob",
      "sagemaker:CreateModelPackage", "sagemaker:DescribeModelPackageGroup", "sagemaker:ListModelPackages",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "PasarRolASageMaker"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.sagemaker.arn]
  }

  statement {
    sid       = "Crawler"
    actions   = ["glue:StartCrawler", "glue:GetCrawler"]
    resources = ["*"]
  }

  statement {
    sid       = "S3Proyecto"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = local.arns_buckets
  }
}

resource "aws_iam_role" "airflow" {
  name               = "${local.prefijo}-airflow"
  assume_role_policy = data.aws_iam_policy_document.confianza_ec2.json
}

resource "aws_iam_role_policy" "airflow" {
  name   = "orquestacion"
  role   = aws_iam_role.airflow.id
  policy = data.aws_iam_policy_document.permisos_airflow.json
}

resource "aws_iam_instance_profile" "airflow" {
  name = "${local.prefijo}-airflow"
  role = aws_iam_role.airflow.name
}
