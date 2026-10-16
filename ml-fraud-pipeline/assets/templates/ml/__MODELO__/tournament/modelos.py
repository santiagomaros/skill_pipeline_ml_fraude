"""Candidatos del torneo y sus espacios de búsqueda de hiperparámetros.

Cada candidato es un Pipeline (preprocesador + modelo): el preprocesador se reajusta en cada fold
de la validación cruzada, así que nada de lo que aprende (medianas, cuartiles, escalado) ve datos de validación.
"""
from __future__ import annotations

from lightgbm import LGBMClassifier
from scipy.stats import loguniform, randint, uniform
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from ml.__MODELO__.config import SEED
from ml.__MODELO__.processor.procesar import construir_preprocesador

PESO_POSITIVA = 1.0         # TODO: razón negativos:positivos de train (EDA); se prueba como hiperparámetro

# Iteraciones de la búsqueda aleatoria por modelo (mismo criterio para todos: se prueba cada espacio con holgura).
N_ITER = {"regresion_logistica": 10, "random_forest": 12, "xgboost": 20, "lightgbm": 20}


def candidatos(con_extra: bool) -> dict[str, tuple[Pipeline, dict]]:
    """{nombre: (pipeline, espacio de hiperparámetros)}. n_jobs=1 en los modelos: el paralelismo está en la validación."""
    lineal = construir_preprocesador("lineal", con_extra)
    arboles = construir_preprocesador("arboles", con_extra)

    return {
        "regresion_logistica": (
            Pipeline([("prep", lineal), ("modelo", LogisticRegression(max_iter=5000))]),
            {"modelo__C": loguniform(1e-3, 1e2), "modelo__class_weight": [None, "balanced"]},
        ),
        "random_forest": (
            Pipeline([("prep", arboles), ("modelo", RandomForestClassifier(n_estimators=300, n_jobs=1, random_state=SEED))]),
            {"modelo__max_depth": [None, 6, 10, 16], "modelo__min_samples_leaf": randint(1, 25),
             "modelo__max_features": ["sqrt", 0.3, 0.5], "modelo__class_weight": [None, "balanced_subsample"]},
        ),
        "xgboost": (
            Pipeline([("prep", arboles), ("modelo", XGBClassifier(tree_method="hist", eval_metric="aucpr", n_jobs=1,
                                                                   random_state=SEED, verbosity=0))]),
            {"modelo__n_estimators": randint(100, 600), "modelo__learning_rate": loguniform(0.02, 0.3),
             "modelo__max_depth": randint(3, 9), "modelo__min_child_weight": randint(1, 11),
             "modelo__subsample": uniform(0.6, 0.4), "modelo__colsample_bytree": uniform(0.5, 0.5),
             "modelo__reg_lambda": loguniform(0.1, 10), "modelo__scale_pos_weight": [1.0, PESO_POSITIVA]},
        ),
        "lightgbm": (
            Pipeline([("prep", arboles), ("modelo", LGBMClassifier(n_jobs=1, random_state=SEED, verbose=-1))]),
            {"modelo__n_estimators": randint(100, 600), "modelo__learning_rate": loguniform(0.02, 0.3),
             "modelo__num_leaves": randint(15, 64), "modelo__min_child_samples": randint(10, 61),
             "modelo__subsample": uniform(0.6, 0.4), "modelo__subsample_freq": [1],
             "modelo__colsample_bytree": uniform(0.5, 0.5), "modelo__reg_lambda": loguniform(0.1, 10),
             "modelo__scale_pos_weight": [1.0, PESO_POSITIVA]},
        ),
    }
