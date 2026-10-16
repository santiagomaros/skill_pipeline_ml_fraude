variable "project" {
  description = "Nombre corto del proyecto (prefijo de los recursos)."
  type        = string
  default     = "__PROYECTO__"
}

variable "environment" {
  description = "Entorno: dev, stg o prod."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "stg", "prod"], var.environment)
    error_message = "environment debe ser dev, stg o prod."
  }
}

variable "region" {
  description = "Región de AWS."
  type        = string
  default     = "us-east-1"
}

variable "owner" {
  description = "Responsable del recurso (etiqueta)."
  type        = string
  default     = "equipo-ml"
}

# ---- S3: ciclo de vida ----
variable "dias_a_ia" {
  description = "Días hasta pasar los objetos a STANDARD_IA."
  type        = number
  default     = 30
}

variable "dias_a_glacier" {
  description = "Días hasta pasar los objetos a GLACIER."
  type        = number
  default     = 90
}

variable "dias_expirar" {
  description = "Días hasta borrar datos y resultados (los modelos y sus metadatos no expiran)."
  type        = number
  default     = 365
}

variable "dias_expirar_versiones" {
  description = "Días que se conservan las versiones anteriores de un objeto."
  type        = number
  default     = 90
}

# ---- Glue ----
variable "cron_crawler" {
  description = "Horario del crawler de Glue (UTC), después de que dbt publica las features."
  type        = string
  default     = "cron(30 6 * * ? *)"
}

# ---- SageMaker ----
variable "imagen_ml" {
  description = "Imagen de contenedor (ECR) con el código de ml/ y sus dependencias."
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/__PROYECTO__-ml:latest"
}

variable "instancia_jobs_ml" {
  description = "Tipo de instancia de los jobs de SageMaker Processing (la usa el DAG de Airflow)."
  type        = string
  default     = "ml.m5.xlarge"
}

variable "crear_endpoint" {
  description = "Crea un endpoint serverless de SageMaker para inferencia en tiempo real (cuesta por uso)."
  type        = bool
  default     = false
}

# ---- EC2 para Airflow ----
variable "crear_ec2_airflow" {
  description = "Crea una instancia EC2 donde corre Airflow."
  type        = bool
  default     = false
}

variable "instancia_airflow" {
  description = "Tipo de instancia EC2 de Airflow."
  type        = string
  default     = "t3.large"
}

variable "subnet_id" {
  description = "Subred donde se crea la EC2 de Airflow (obligatoria si crear_ec2_airflow = true)."
  type        = string
  default     = null
}

variable "cidr_acceso_airflow" {
  description = "Rangos CIDR con acceso a la interfaz web de Airflow (puerto 8080). Vacío = sin acceso entrante."
  type        = list(string)
  default     = []
}
