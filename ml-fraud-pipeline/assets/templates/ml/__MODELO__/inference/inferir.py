"""Stage `inference`: puntúa operaciones con el modelo campeón y guarda el resultado de producción.

Entrada : tabla de features de dbt (`mart_fraude_features`), igual que en entrenamiento.
Salida  : tabla `scores_fraude` (row_id, score, particion, modelo_version, fecha_scoring) en DuckDB.
El score es la probabilidad de fraude. El modelo es un Pipeline (preprocesador + LightGBM): aplica exactamente
el mismo preprocesamiento con el que se entrenó, sin recalcular nada con los datos nuevos.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import duckdb
import joblib
import pandas as pd
from sklearn.metrics import average_precision_score

from ml.__MODELO__.config import ARTEFACTOS, CAMPEON_ARCHIVO, ID, RESULTADOS, RESULTADOS_DB, TARGET
from ml.__MODELO__.processor.procesar import cargar_mart, separar_xy


def cargar_campeon(ruta=CAMPEON_ARCHIVO):
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Ejecuta antes el torneo (tournament/torneo.py).")
    return joblib.load(ruta)


def version_modelo(ruta=CAMPEON_ARCHIVO) -> str:
    """Identificador corto del archivo del modelo, para saber con qué versión se generó cada score."""
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:8]


def validar_esquema(modelo, X: pd.DataFrame) -> None:
    """Falla si faltan columnas que el modelo necesita (protege contra cambios en el mart de dbt)."""
    requeridas = list(modelo.named_steps["prep"].feature_names_in_)
    faltan = [c for c in requeridas if c not in X.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en los datos a puntuar: {faltan}")


def puntuar(modelo, df: pd.DataFrame) -> pd.Series:
    """Probabilidad de fraude de cada fila de `df` (con las columnas del mart)."""
    X = df.drop(columns=[c for c in (TARGET, ID) if c in df.columns])
    validar_esquema(modelo, X)
    return pd.Series(modelo.predict_proba(X)[:, 1], index=df.index, name="score")


def cargar_particion() -> dict[int, str]:
    """row_id -> 'train' | 'test' (la guarda el processor)."""
    p = json.load(open(ARTEFACTOS / "particion.json"))
    return {**{i: "train" for i in p["train"]}, **{i: "test" for i in p["test"]}}


def main() -> None:
    modelo, version = cargar_campeon(), version_modelo()
    df = cargar_mart()
    scores = puntuar(modelo, df)
    particion = df[ID].map(cargar_particion())
    salida = pd.DataFrame({ID: df[ID], "score": scores, "particion": particion, "modelo_version": version,
                           "fecha_scoring": datetime.now(timezone.utc).replace(tzinfo=None)})

    RESULTADOS_DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(RESULTADOS_DB))
    con.register("salida", salida)
    con.execute("create or replace table scores_fraude as select * from salida")
    con.close()
    print(f"scores_fraude: {len(salida):,} filas | modelo {version} | {RESULTADOS_DB}")

    # Control de consistencia: el PR-AUC en test debe coincidir con el que reportó el torneo.
    es_test = particion == "test"
    pr_auc = average_precision_score(df.loc[es_test, TARGET], scores[es_test])
    torneo = json.load(open(RESULTADOS / "torneo.json"))
    esperado = next(f["test_pr_auc"] for f in torneo["fase2_confirmacion"]
                    if (f["variante"], f["modelo"]) == (torneo["campeon"]["variante"], torneo["campeon"]["modelo"]))
    print(f"PR-AUC en test: {pr_auc:.4f} (torneo: {esperado:.4f})")
    assert abs(pr_auc - esperado) < 1e-6, "el modelo cargado no reproduce el resultado del torneo"


if __name__ == "__main__":
    main()
