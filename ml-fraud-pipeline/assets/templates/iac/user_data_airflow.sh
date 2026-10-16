#!/bin/bash
# Arranque de la EC2 de Airflow (simulación): instala Docker y deja listo el despliegue de Airflow.
set -euo pipefail
dnf install -y docker git
systemctl enable --now docker
mkdir -p /opt/airflow
# En un despliegue real: clonar el repositorio, copiar airflow/dags y levantar Airflow con docker compose.
echo "Airflow listo para desplegarse en /opt/airflow" > /var/log/airflow-bootstrap.log
