"""Stage `recommended`: convierte los scores en recomendaciones de prevención de fraude.

Para cada operación: una ACCIÓN y los MOTIVOS que más empujan el riesgo hacia arriba.

Política (por bandas de score), de menos a más severa:
  aprobar  <  autenticacion_adicional (p. ej. 3DS/OTP)  <  revision_manual  <  rechazar
Los umbrales se fijan con una PRECISIÓN ACUMULADA objetivo para cada banda: "todo lo que cae en esta banda o
por encima de ella es fraude, al menos, el X% de las veces". Se calculan con predicciones fuera de muestra
(validación cruzada sobre train): nunca con test ni con scores en muestra. Test solo sirve para evaluar la política.

Aviso: la prevalencia de fraude de la muestra puede diferir de la de producción, así que las precisiones objetivo y los
volúmenes por banda NO se trasladan a producción. En producción los umbrales se reajustan con la prevalencia real,
la capacidad de revisión manual y el costo de cada decisión (rechazar un cliente bueno vs. aprobar un fraude).
"""
from __future__ import annotations

import json

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from ml.__MODELO__.config import COLUMNA_MONTO, COLUMNA_SEGMENTO, ID, MODELO_DIR, RESULTADOS_DB, SEED, TARGET
from ml.__MODELO__.inference.inferir import cargar_campeon, version_modelo
from ml.__MODELO__.processor.procesar import cargar_mart, particionar, separar_xy

SALIDA = MODELO_DIR / "recommended" / "resultados"

# Parámetros de negocio (ajustables): precisión acumulada mínima que debe tener cada banda.
PRECISIONES_OBJETIVO = {"rechazar": 0.90, "revision_manual": 0.70, "autenticacion_adicional": 0.50}
ACCIONES = ["aprobar", "autenticacion_adicional", "revision_manual", "rechazar"]     # de menor a mayor severidad
TOP_MOTIVOS = 3


def calibrar_umbrales(modelo, X_train, y_train, precisiones=PRECISIONES_OBJETIVO) -> dict[str, float]:
    """Umbrales de score a partir de predicciones fuera de muestra (5 folds) sobre train."""
    oof = cross_val_predict(clone(modelo), X_train, y_train, cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                            method="predict_proba", n_jobs=5)[:, 1]
    precision, _, umbrales = precision_recall_curve(y_train, oof)
    out = {}
    for accion, objetivo in precisiones.items():
        i = int(np.argmax(precision[:-1] >= objetivo))          # primer umbral que alcanza la precisión objetivo
        out[accion] = float(umbrales[i])
    return out


def asignar_accion(scores, umbrales: dict[str, float]) -> pd.Series:
    s = np.asarray(scores)
    accion = np.full(len(s), "aprobar", dtype=object)
    for nombre in ("autenticacion_adicional", "revision_manual", "rechazar"):     # de menor a mayor umbral
        accion[s >= umbrales[nombre]] = nombre
    return pd.Series(accion, dtype="object")


def _contribuciones(modelo, Xt):
    """Contribución de cada variable al score en log-odds (sin la columna del sesgo).
    Exactas para LightGBM, XGBoost y regresión logística; para otros modelos devuelve None."""
    m = modelo.named_steps["modelo"]
    nombre = type(m).__name__
    if nombre == "LGBMClassifier":
        return m.predict(Xt, pred_contrib=True)[:, :-1]
    if nombre == "XGBClassifier":
        import xgboost as xgb
        return m.get_booster().predict(xgb.DMatrix(Xt), pred_contribs=True)[:, :-1]
    if nombre == "LogisticRegression":
        return Xt.to_numpy(dtype=float) * m.coef_[0]          # el preprocesador ya estandariza: contribución = coeficiente x valor
    return None


def motivos(modelo, X: pd.DataFrame, k: int = TOP_MOTIVOS) -> list[str]:
    """Las k variables que más aumentan el riesgo de cada fila. Si el modelo no ofrece contribuciones exactas
    (p. ej. Random Forest), devuelve cadenas vacías: usar un boosting o añadir `shap` si se necesitan motivos."""
    Xt = modelo.named_steps["prep"].transform(X)
    contrib = _contribuciones(modelo, Xt)
    if contrib is None:
        return [""] * len(X)
    nombres = list(Xt.columns); valores = Xt.to_numpy()
    out = []
    for i in range(len(X)):
        top = np.argsort(-contrib[i])[:k]
        out.append("; ".join(f"{nombres[j]}={'faltante' if pd.isna(valores[i, j]) else format(valores[i, j], 'g')} (+{contrib[i, j]:.2f})"
                             for j in top if contrib[i, j] > 0))
    return out


def impulsores_globales(modelo, X: pd.DataFrame) -> pd.Series:
    """Qué variables mueven más el score: importancia media absoluta de las contribuciones o, si no hay, la del modelo."""
    Xt = modelo.named_steps["prep"].transform(X)
    contrib = _contribuciones(modelo, Xt)
    m = modelo.named_steps["modelo"]
    if contrib is not None:
        serie = pd.Series(np.abs(contrib).mean(0), index=Xt.columns)
    elif hasattr(m, "feature_importances_"):
        serie = pd.Series(m.feature_importances_, index=Xt.columns)
    else:
        serie = pd.Series(dtype=float)
    return serie.sort_values(ascending=False)


def resumen_por_accion(df: pd.DataFrame) -> pd.DataFrame:
    """Evaluación de la política sobre test (usa la etiqueta solo para medir)."""
    total, fraude_total, monto_fraude = len(df), df[TARGET].sum(), df.loc[df[TARGET] == 1, COLUMNA_MONTO].sum()
    filas = []
    for a in ACCIONES:
        g = df[df["accion"] == a]
        filas.append({"accion": a, "operaciones": len(g), "pct_operaciones": len(g) / total,
                      "tasa_fraude": g[TARGET].mean() if len(g) else np.nan, "fraudes": int(g[TARGET].sum()),
                      "pct_fraude_capturado": g[TARGET].sum() / fraude_total,
                      "pct_monto_fraude": g.loc[g[TARGET] == 1, COLUMNA_MONTO].sum() / monto_fraude})
    return pd.DataFrame(filas)


def main() -> None:
    modelo, version = cargar_campeon(), version_modelo()
    df = cargar_mart(); train, test = particionar(df)
    X_tr, y_tr = separar_xy(train)

    umbrales = calibrar_umbrales(modelo, X_tr, y_tr)
    SALIDA.mkdir(parents=True, exist_ok=True)
    json.dump({"modelo_version": version, "precisiones_objetivo": PRECISIONES_OBJETIVO, "umbrales_score": umbrales,
               "origen": "predicciones fuera de muestra (CV 5 folds) sobre train"},
              open(SALIDA / "politica.json", "w"), indent=1, ensure_ascii=False)

    # Scores de la etapa `inference` + acción y motivos
    con = duckdb.connect(str(RESULTADOS_DB))
    sc = con.sql("select row_id, score, particion from scores_fraude").df()
    base = df.merge(sc, on=ID)
    base["accion"] = asignar_accion(base["score"], umbrales)
    X_all, _ = separar_xy(df)
    base["motivos"] = ""
    marcado = base["accion"] != "aprobar"
    base.loc[marcado, "motivos"] = motivos(modelo, X_all.loc[marcado.values])
    out = base[[ID, "score", "accion", "motivos", "particion"]].assign(modelo_version=version)
    con.register("out", out); con.execute("create or replace table recomendaciones as select * from out"); con.close()

    # ---- Evaluación en test ----
    t = base[base["particion"] == "test"]
    resumen = resumen_por_accion(t)
    acum = {}
    for a in ("autenticacion_adicional", "revision_manual", "rechazar"):          # precisión acumulada real en test
        g = t[t["score"] >= umbrales[a]]
        acum[a] = (len(g) / len(t), g[TARGET].mean())
    impulsores = impulsores_globales(modelo, X_all.loc[(base["particion"] == "test").values]).head(10)
    por_segmento = t.groupby(COLUMNA_SEGMENTO).agg(operaciones=(ID, "size"), tasa_fraude=(TARGET, "mean"), score_medio=("score", "mean"),
                                      pct_revision_o_rechazo=("accion", lambda s: s.isin(["revision_manual", "rechazar"]).mean()))

    md = ["# Recomendaciones de prevención de fraude", "",
          f"Modelo `{version}` (campeón del torneo). Evaluación sobre test ({len(t):,} operaciones, {t[TARGET].mean():.1%} de fraude).", "",
          "> Las precisiones y los volúmenes dependen de la prevalencia de fraude de la muestra; no se trasladan directamente a producción.", "",
          "## Política", "",
          "| Acción | Umbral de score | Precisión acumulada objetivo | Precisión acumulada real en test | % de operaciones con score ≥ umbral |", "|---|---|---|---|---|"]
    md += [f"| {a} | {umbrales[a]:.3f} | {PRECISIONES_OBJETIVO[a]:.0%} | {acum[a][1]:.1%} | {acum[a][0]:.1%} |"
           for a in ("autenticacion_adicional", "revision_manual", "rechazar")]
    md += ["", "Los umbrales salen de predicciones fuera de muestra sobre train; la columna «real en test» es la comprobación independiente.", "",
           "## Resultado por acción (test)", "",
           "| Acción | Operaciones | % operaciones | Tasa de fraude | Fraudes | % del fraude capturado | % del monto de fraude |", "|---|---|---|---|---|---|---|"]
    md += [f"| {r.accion} | {r.operaciones:,} | {r.pct_operaciones:.1%} | {r.tasa_fraude:.1%} | {r.fraudes} | {r.pct_fraude_capturado:.1%} | {r.pct_monto_fraude:.1%} |"
           for r in resumen.itertuples()]
    md += ["", "«Aprobar» incluye el fraude que se escapa: su tasa de fraude y su % del fraude son el riesgo residual de la política.", "",
           "## Qué empuja más el score (importancia por variable)", "", "| Variable | Importancia |", "|---|---|"]
    md += [f"| {n} | {v:.3f} |" for n, v in impulsores.items()]
    md += ["", "## Por segmento (test)", "", "| Segmento | Operaciones | Tasa de fraude | Score medio | % en revisión o rechazo |", "|---|---|---|---|---|"]
    md += [f"| {p} | {int(r.operaciones):,} | {r.tasa_fraude:.1%} | {r.score_medio:.3f} | {r.pct_revision_o_rechazo:.1%} |" for p, r in por_segmento.iterrows()]
    ejemplo = t[t["accion"] == "rechazar"].sort_values("score", ascending=False).head(3)
    md += ["", "## Ejemplos de motivos (operaciones rechazadas con mayor score)", ""]
    md += [f"- fila {r.row_id}: score {r.score:.3f} → {r.motivos}" for r in ejemplo.itertuples()]
    n_segmento = sum(v.startswith(f"{COLUMNA_SEGMENTO}_") for v in impulsores.index)
    md += ["", "## Recomendaciones", "",
           "1. **Aplicar la política por bandas** con los umbrales de arriba como punto de partida; en producción reajustarlos con la prevalencia real, la capacidad de revisión manual y el costo de cada decisión.",
           "2. **Priorizar la revisión manual** en la banda intermedia: concentra operaciones con riesgo alto pero no concluyente; los motivos orientan al analista.",
           f"3. **Tratar con cautela las variables de segmento:** {n_segmento} de las 10 variables más influyentes son categorías de `{COLUMNA_SEGMENTO}`; si pueden reflejar cómo se armó la muestra, validarlas con datos reales antes de basar reglas en ellas.",
           "4. **Monitorear** la distribución del score, la tasa por banda y la deriva de las variables más influyentes; reentrenar si se degradan.", ""]
    (SALIDA / "recomendaciones.md").write_text("\n".join(md))
    print("\n".join(md[:30]))


if __name__ == "__main__":
    main()
