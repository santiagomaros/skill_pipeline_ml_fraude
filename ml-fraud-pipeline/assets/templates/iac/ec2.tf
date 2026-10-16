# EC2 para Airflow (opcional). Imagen de Amazon Linux 2023 vigente, leída del parámetro público de AWS.
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_subnet" "airflow" {
  count = var.crear_ec2_airflow ? 1 : 0

  id = var.subnet_id
}

resource "aws_security_group" "airflow" {
  count = var.crear_ec2_airflow ? 1 : 0

  name        = "${local.prefijo}-airflow"
  description = "Acceso a la interfaz web de Airflow"
  vpc_id      = data.aws_subnet.airflow[0].vpc_id

  dynamic "ingress" {
    for_each = var.cidr_acceso_airflow

    content {
      description = "Interfaz web de Airflow"
      from_port   = 8080
      to_port     = 8080
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "airflow" {
  count = var.crear_ec2_airflow ? 1 : 0

  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instancia_airflow
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.airflow[0].id]
  iam_instance_profile   = aws_iam_instance_profile.airflow.name
  user_data              = file("${path.module}/user_data_airflow.sh")

  metadata_options {
    http_tokens = "required" # IMDSv2
  }

  root_block_device {
    volume_size = 50
    encrypted   = true
  }

  tags = { Name = "${local.prefijo}-airflow" }

  lifecycle {
    precondition {
      condition     = var.subnet_id != null
      error_message = "Define subnet_id cuando crear_ec2_airflow = true."
    }
  }
}
