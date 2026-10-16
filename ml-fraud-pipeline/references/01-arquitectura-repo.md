# Arquitectura del repositorio

## Estructura

```
<proyecto>/
├── dbt/                 capa SQL de features: stg → int → mart, con pruebas
├── ml/<modelo>/
│   ├── config.py        rutas, semilla, columnas
│   ├── processor/       partición y preprocesadores que aprenden de train
│   ├── tournament/      modelos, métricas y torneo (validación cruzada anidada)
│   ├── inference/       scores con el modelo campeón
│   └── recommended/     acciones de prevención y motivos
├── airflow/dags/        DAG diario  ·  airflow/tests/ verificación de estructura
├── iac/                 Terraform (S3, IAM, Glue, SageMaker, EC2)
├── src/eda/             cuaderno del EDA y helpers
├── reports/             informe (docx/pdf), figuras y el script que las genera
├── requirements.txt     versiones fijadas (==)
└── README.md
```

Usa `scripts/scaffold.py` para crearla. Los nombres de las etapas (`processor`, `tournament`, `inference`, `recommended`) son
parte del contrato del proyecto: se corrigen **antes** de escribir código que los importe (`git mv`).

## Flujo de ramas

`main` (producción) · `release` (preparación) · `dev` (integración) · `feature/<nombre>` (trabajo). El código llega a `main`
pasando por `dev` y `release` con pull requests, en ese orden. Crea `main` con un primer commit mínimo (`.gitignore`), luego
`dev` y `release` desde `main` y la `feature` desde `dev`. Es una simulación de promoción a producción; no hace falta
protección de ramas para el ejercicio, pero sí revisar cada PR.

## Entorno

- Un entorno virtual por proyecto y `requirements.txt` con versiones fijadas (`pip freeze`).
- XGBoost y LightGBM en macOS necesitan OpenMP: `brew install libomp` (pídelo al usuario; es software del sistema).
- Verifica la versión de Python antes de prometer librerías: Airflow no soporta aún las versiones más nuevas de Python, y
  conviene ejecutar su DAG solo en un entorno aparte o verificarlo con el script de estructura.
- Ejecuta los módulos con `python -m ml.<modelo>.<etapa>.<modulo>` desde la raíz del proyecto (necesitan `ml/__init__.py`).

## Qué se versiona y qué no

- **No se versiona:** datos de entrada (CSV), estados de Terraform (`*.tfstate`), `*.tfvars`, `.terraform/`, base DuckDB de
  dbt (`*.duckdb`), `dbt/target`, modelos y artefactos (`*.joblib`, carpeta `artefactos/`), `.venv`.
- **Sí se versiona:** `.terraform.lock.hcl`, resultados del torneo en JSON/Markdown, figuras del informe, la documentación.
- El repositorio es **privado** si los datos o el enunciado son confidenciales. Quien clone debe copiar el CSV a mano;
  documéntalo en el README.
- Nunca credenciales en el código: variables de entorno o gestor de secretos. `verificar_proyecto.py` busca patrones típicos.

## README mínimo

Objetivo, estructura, cómo ejecutarlo (los cinco comandos del flujo), qué se verificó y qué es simulación, y dónde está el
informe.
