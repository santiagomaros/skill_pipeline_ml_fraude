"""Configuración común del modelo de fraude: rutas, semilla y columnas del mart de dbt."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MODELO_DIR = RAIZ / "ml" / "__MODELO__"

# Mart generado por dbt (ver dbt/README.md). Se puede cambiar con la variable MART_DUCKDB.
DUCKDB = Path(os.environ.get("MART_DUCKDB", RAIZ / "dbt" / "target" / "fraude.duckdb"))
TABLA_MART = "mart_features"

ARTEFACTOS = MODELO_DIR / "artefactos"                  # modelos y preprocesadores (no se versionan)
RESULTADOS = MODELO_DIR / "tournament" / "resultados"   # tablas del torneo (JSON y Markdown, sí se versionan)

SEED = 42
TEST_SIZE = 0.20
TARGET = "objetivo"  # TODO: columna objetivo del mart
ID = "row_id"

# Campeón del torneo (ver tournament/resultados/torneo.md).
CAMPEON_ARCHIVO = ARTEFACTOS / "modelo_campeon.joblib"
RESULTADOS_DB = ARTEFACTOS / "resultados.duckdb"        # tablas de salida: scores_fraude y recomendaciones

# Columnas del mart que usa `recommended` (ajustar al proyecto).
COLUMNA_MONTO = "monto"          # importe de la operación (para medir el monto de fraude capturado)
COLUMNA_SEGMENTO = "segmento"    # variable de segmento para el resumen por grupos (p. ej. país agrupado)
