"""Torneo de modelos: regresión logística, Random Forest, XGBoost y LightGBM, cada uno con y sin un grupo de variables sospechosas (ablación).

Protocolo (sin variable temporal no hay backtesting fuera de tiempo: se usa validación cruzada estratificada):
  Fase 1 · Selección. Validación cruzada ANIDADA sobre train: el bucle interno elige hiperparámetros y el externo
           estima el desempeño con datos que esa búsqueda no vio. El campeón se elige aquí, por PR-AUC media.
  Fase 2 · Confirmación. Cada candidato se reajusta con toda train (búsqueda con 5 folds) y se evalúa UNA vez en test.
           Test no interviene en ninguna decisión; solo se reporta.

Uso (desde la raíz del proyecto):  python -m ml.__MODELO__.tournament.torneo [--rapido]
"""
from __future__ import annotations

import argparse
import json
import time
import warnings

import joblib
import numpy as np
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, cross_validate

from ml.__MODELO__.config import ARTEFACTOS, RESULTADOS, SEED, TARGET
from ml.__MODELO__.processor.procesar import cargar_mart, particionar, separar_xy
from ml.__MODELO__.tournament import metricas
from ml.__MODELO__.tournament.modelos import N_ITER, candidatos

warnings.filterwarnings("ignore", category=UserWarning)


def busqueda(pipeline, espacio, n_iter, folds, n_jobs):
    return RandomizedSearchCV(pipeline, espacio, n_iter=n_iter, scoring="average_precision",
                              cv=StratifiedKFold(folds, shuffle=True, random_state=SEED),
                              random_state=SEED, n_jobs=n_jobs, refit=True)


def fase_seleccion(X, y, args) -> list[dict]:
    externo = StratifiedKFold(args.folds_externos, shuffle=True, random_state=SEED)
    filas = []
    for variante, con_extra in (("con_extra", True), ("sin_extra", False)):
        for nombre, (pipe, espacio) in candidatos(con_extra).items():
            t0 = time.time()
            n_iter = max(2, N_ITER[nombre] // args.reduccion)
            res = cross_validate(busqueda(pipe, espacio, n_iter, args.folds_internos, 1), X, y, cv=externo,
                                 scoring=metricas.SCORERS, n_jobs=args.folds_externos, return_estimator=True)
            por_fold = {m: res[f"test_{m}"] * (-1 if m == "brier" else 1) for m in metricas.SCORERS}
            fila = {"variante": variante, "modelo": nombre, "segundos": round(time.time() - t0, 1),
                    "pr_auc_por_fold": [round(float(v), 4) for v in por_fold["pr_auc"]],
                    "hiperparametros_por_fold": [e.best_params_ for e in res["estimator"]]}
            for m, v in por_fold.items():
                fila[f"{m}_media"], fila[f"{m}_desv"] = float(np.mean(v)), float(np.std(v, ddof=1))
            filas.append(fila)
            print(f"[fase 1] {variante:9s} {nombre:19s} PR-AUC {fila['pr_auc_media']:.4f} ± {fila['pr_auc_desv']:.4f} "
                  f"({fila['segundos']} s)", flush=True)
    return filas


def fase_confirmacion(X_tr, y_tr, X_te, y_te, args):
    filas, modelos = [], {}
    for variante, con_extra in (("con_extra", True), ("sin_extra", False)):
        for nombre, (pipe, espacio) in candidatos(con_extra).items():
            t0 = time.time()
            n_iter = max(2, N_ITER[nombre] // args.reduccion)
            b = busqueda(pipe, espacio, n_iter, args.folds_externos, -1).fit(X_tr, y_tr)
            p = b.predict_proba(X_te)[:, 1]
            fila = {"variante": variante, "modelo": nombre, "cv_pr_auc_mejor": float(b.best_score_),
                    "hiperparametros": {k: (v.item() if hasattr(v, "item") else v) for k, v in b.best_params_.items()},
                    **{f"test_{k}": v for k, v in metricas.calcular(y_te, p).items()}, "segundos": round(time.time() - t0, 1)}
            filas.append(fila); modelos[(variante, nombre)] = b.best_estimator_
            print(f"[fase 2] {variante:9s} {nombre:19s} test PR-AUC {fila['test_pr_auc']:.4f} | ROC-AUC {fila['test_roc_auc']:.4f}", flush=True)
    return filas, modelos


def tabla_md(filas, columnas, titulos) -> str:
    out = ["| " + " | ".join(titulos) + " |", "|" + "---|" * len(titulos)]
    for f in filas:
        out.append("| " + " | ".join(c(f) if callable(c) else str(f[c]) for c in columnas) + " |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true", help="prueba de humo: pocos folds e iteraciones")
    args = ap.parse_args()
    args.folds_externos, args.folds_internos, args.reduccion = (3, 2, 4) if args.rapido else (5, 3, 1)

    train, test = particionar(cargar_mart())
    X_tr, y_tr = separar_xy(train); X_te, y_te = separar_xy(test)
    prevalencia = float(y_tr.mean())
    print(f"train {X_tr.shape} ({prevalencia:.2%} fraude) | test {X_te.shape} | línea base PR-AUC = {prevalencia:.3f}", flush=True)

    seleccion = fase_seleccion(X_tr, y_tr, args)
    seleccion.sort(key=lambda f: -f["pr_auc_media"])
    campeon = seleccion[0]
    print(f"\nCampeón (Fase 1): {campeon['variante']} / {campeon['modelo']}", flush=True)

    confirmacion, modelos = fase_confirmacion(X_tr, y_tr, X_te, y_te, args)
    confirmacion.sort(key=lambda f: -f["test_pr_auc"])

    sufijo = "_rapido" if args.rapido else ""
    RESULTADOS.mkdir(parents=True, exist_ok=True); ARTEFACTOS.mkdir(parents=True, exist_ok=True)
    resumen = {"linea_base_pr_auc": prevalencia, "campeon": {"variante": campeon["variante"], "modelo": campeon["modelo"]},
               "fase1_seleccion": seleccion, "fase2_confirmacion": confirmacion, "semilla": SEED,
               "protocolo": {"folds_externos": args.folds_externos, "folds_internos": args.folds_internos}}
    json.dump(resumen, open(RESULTADOS / f"torneo{sufijo}.json", "w"), indent=1, ensure_ascii=False)
    joblib.dump(modelos[(campeon["variante"], campeon["modelo"])], ARTEFACTOS / f"modelo_campeon{sufijo}.joblib")

    f = lambda c: (lambda r: f"{r[c + '_media']:.4f} ± {r[c + '_desv']:.4f}")
    md = ["# Resultados del torneo", "", f"Línea base (clasificador aleatorio): PR-AUC = {prevalencia:.3f}.", "",
          "## Fase 1 — validación cruzada anidada sobre train (media ± desv. de los folds externos)", "",
          tabla_md(seleccion, ["variante", "modelo", f("pr_auc"), f("roc_auc"), f("f1_max"), f("recall_a_precision_80"), f("brier"), "segundos"],
                   ["Variante", "Modelo", "PR-AUC", "ROC-AUC", "F1 máx.", "Recall a precisión 80%", "Brier", "Seg."]), "",
          f"**Campeón (mayor PR-AUC media): {campeon['variante']} / {campeon['modelo']}**", "",
          "## Fase 2 — modelos reajustados con todo train y evaluados una vez en test", "",
          tabla_md(confirmacion, ["variante", "modelo", lambda r: f"{r['test_pr_auc']:.4f}", lambda r: f"{r['test_roc_auc']:.4f}",
                                  lambda r: f"{r['test_f1_max']:.4f}", lambda r: f"{r['test_recall_a_precision_80']:.4f}",
                                  lambda r: f"{r['test_brier']:.4f}"],
                   ["Variante", "Modelo", "PR-AUC", "ROC-AUC", "F1 máx.", "Recall a precisión 80%", "Brier"]), ""]
    (RESULTADOS / f"torneo{sufijo}.md").write_text("\n".join(md))
    print(f"\nResultados en {RESULTADOS}", flush=True)


if __name__ == "__main__":
    main()
