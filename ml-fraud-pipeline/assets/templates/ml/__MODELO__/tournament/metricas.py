"""Métricas del torneo. La principal es PR-AUC (precisión promedio): la línea base de un clasificador aleatorio es la prevalencia del objetivo."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss, make_scorer,
                             precision_recall_curve, roc_auc_score)

PRECISION_MINIMA = 0.80     # para "recall a precisión fija"


def recall_a_precision(y, p, minimo: float = PRECISION_MINIMA) -> float:
    """Mayor recall alcanzable manteniendo al menos `minimo` de precisión."""
    precision, recall, _ = precision_recall_curve(y, p)
    ok = precision >= minimo
    return float(recall[ok].max()) if ok.any() else 0.0


def f1_maximo(y, p) -> float:
    precision, recall, _ = precision_recall_curve(y, p)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-12, None)
    return float(f1.max())


def calcular(y, p) -> dict:
    """Todas las métricas a partir de la probabilidad de la clase positiva."""
    return {
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "f1_max": f1_maximo(y, p),
        "recall_a_precision_80": recall_a_precision(y, p),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p)),
    }


# Scorers para cross_validate (el nombre es la clave del diccionario de resultados).
SCORERS = {
    "pr_auc": "average_precision",
    "roc_auc": "roc_auc",
    "f1_max": make_scorer(f1_maximo, response_method="predict_proba"),
    "recall_a_precision_80": make_scorer(recall_a_precision, response_method="predict_proba"),
    "brier": make_scorer(brier_score_loss, response_method="predict_proba", greater_is_better=False),
}
