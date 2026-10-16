"""Stage `processor`: del mart de dbt a datos listos para modelar.

Reparto con dbt (ver dbt/README.md): dbt hace lo que NO aprende de los datos; este módulo hace lo que SÍ:
partición train/test, imputación con la mediana, escalado, cuartiles de `monto` y one-hot.

Los preprocesadores se construyen sin ajustar. Quien los use debe ajustarlos solo con train:
 - en validación cruzada van dentro del Pipeline, así se reajustan en cada fold (sin fuga);
 - `main()` los ajusta con todo train y los guarda para `inference`.
"""
from __future__ import annotations

import json

import duckdb
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer, OneHotEncoder, StandardScaler

from ml.__MODELO__.config import ARTEFACTOS, DUCKDB, ID, SEED, TABLA_MART, TARGET, TEST_SIZE

# TODO: completar con las decisiones del EDA (nombres de las columnas del mart de dbt).
FLAGS = []            # indicadores 0/1 creados por dbt (faltantes, centinelas, x > 0, ...)

# Modelos lineales: variables con tope o log1p de dbt, imputadas con la mediana y estandarizadas.
LINEAL_NUM = []
LINEAL_CAT = []       # categóricas que se codifican one-hot
LINEAL_BINS = []      # numéricas con relación no monótona: se discretizan en cuartiles aprendidos de train

# Modelos de árboles: valores limpios sin transformar (los NaN los manejan los propios modelos).
ARBOLES_NUM = []

# Grupo de variables sospechosas para la ablación "con y sin" (p. ej. una variable que puede ser artefacto del muestreo).
CATEGORIA_EXTRA = "segmento"


def cargar_mart(ruta=DUCKDB) -> pd.DataFrame:
    """Lee el mart de dbt ordenado por row_id (el orden del archivo de origen)."""
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Ejecuta antes `dbt build` (ver dbt/README.md).")
    con = duckdb.connect(str(ruta), read_only=True)
    try:
        return con.sql(f"select * from {TABLA_MART} order by {ID}").df()
    finally:
        con.close()


def particionar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """80/20 estratificado por el objetivo. Misma partición que el EDA (misma semilla y mismo orden de filas)."""
    train, test = train_test_split(df, test_size=TEST_SIZE, stratify=df[TARGET], random_state=SEED)
    return train.reset_index(drop=True), test.reset_index(drop=True)


def separar_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return df.drop(columns=[TARGET, ID]), df[TARGET]


def construir_preprocesador(familia: str, con_extra: bool = True) -> ColumnTransformer:
    """Preprocesador SIN ajustar. familia: 'lineal' (regresión logística) o 'arboles' (RF, XGBoost, LightGBM)."""
    extra = [CATEGORIA_EXTRA] if con_extra else []
    onehot = OneHotEncoder(handle_unknown="ignore", sparse_output=False)

    if familia == "lineal":
        piezas = [
            ("num", Pipeline([("imputar", SimpleImputer(strategy="median")), ("escalar", StandardScaler())]), LINEAL_NUM),
            ("monto", KBinsDiscretizer(n_bins=4, encode="onehot-dense", strategy="quantile"), LINEAL_BINS),
            ("cat", onehot, LINEAL_CAT + extra),
            ("flags", "passthrough", FLAGS),
        ]
    elif familia == "arboles":
        piezas = [
            ("num", "passthrough", ARBOLES_NUM),
            ("cat", onehot, extra) if extra else None,
            ("flags", "passthrough", FLAGS),
        ]
        piezas = [p for p in piezas if p is not None]
    else:
        raise ValueError(f"familia desconocida: {familia!r}")

    return ColumnTransformer(piezas, remainder="drop", verbose_feature_names_out=False).set_output(transform="pandas")


def main() -> None:
    """Parte los datos, ajusta los preprocesadores con todo train y guarda artefactos para `inference`."""
    df = cargar_mart()
    train, test = particionar(df)
    X_train, _ = separar_xy(train)
    print(f"mart: {df.shape} | train: {train.shape} ({train[TARGET].mean():.2%} fraude) | test: {test.shape} ({test[TARGET].mean():.2%} fraude)")

    ARTEFACTOS.mkdir(parents=True, exist_ok=True)
    json.dump({"train": train[ID].tolist(), "test": test[ID].tolist()}, open(ARTEFACTOS / "particion.json", "w"))
    for familia in ("lineal", "arboles"):
        for con_extra in (True, False):
            pre = construir_preprocesador(familia, con_extra).fit(X_train)
            nombre = f"preprocesador_{familia}_{'con' if con_extra else 'sin'}_extra.joblib"
            joblib.dump(pre, ARTEFACTOS / nombre)
            print(f"  {nombre}: {len(pre.get_feature_names_out())} columnas de salida")


if __name__ == "__main__":
    main()
