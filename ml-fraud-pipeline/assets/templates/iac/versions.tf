terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Estado remoto (referencia; no se activa en esta simulación). Requiere un bucket y una tabla DynamoDB previos:
  # backend "s3" {
  #   bucket         = "<bucket-estado-terraform>"
  #   key            = "__PROYECTO__/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "<tabla-bloqueo>"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

data "aws_caller_identity" "actual" {}
