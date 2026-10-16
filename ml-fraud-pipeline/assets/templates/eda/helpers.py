"""Funciones de apoyo del EDA de detección de fraude (extraídas de un proyecto real y verificadas).

Se importan en el cuaderno: from helpers import wilson, auc_rank, auc_ic, cochran_armitage, capear, tramos
"""
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import rankdata


def wilson(k, n, alpha=0.05):
    """IC de Wilson para una proporción k/n (mejor que el normal con proporciones pequeñas o extremas)."""
    ci = stats.binomtest(int(k), int(n)).proportion_ci(confidence_level=1 - alpha, method="wilson")
    return ci.low, ci.high


def auc_rank(x, y):
    """AUC de Mann-Whitney: P(valor de un positivo > valor de un negativo); 0,5 = sin señal. x, y: arrays numpy."""
    r = rankdata(x); n1 = int(y.sum()); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def auc_ic(x, y, B=300, seed=42):
    """IC95% por bootstrap de la AUC."""
    rng = np.random.default_rng(seed); idx = np.arange(len(x)); aucs = []
    for _ in range(B):
        i = rng.choice(idx, len(idx), replace=True)
        aucs.append(auc_rank(x[i], y[i]))
    return np.percentile(aucs, [2.5, 97.5])


def capear(s, minimo=50):
    """Agrupa la cola rara de una discreta: valores con menos de `minimo` filas se reúnen en '>= k'."""
    cuentas = s.value_counts().sort_index()
    tope = cuentas[cuentas >= minimo].index.max()
    return s.clip(upper=tope), tope


def cochran_armitage(x, y):
    """z y p de la tendencia lineal en la proporción del objetivo según el valor ordinal x (Series con el mismo índice)."""
    p = y.mean(); n = pd.Series(1, index=x.index).groupby(x).sum(); r = y.groupby(x).sum()
    xs = n.index.to_numpy(float)
    num = (xs * (r.to_numpy() - n.to_numpy() * p)).sum()
    den = np.sqrt(p * (1 - p) * ((n.to_numpy() * xs**2).sum() - (n.to_numpy() * xs).sum()**2 / n.sum()))
    z = num / den
    return z, 2 * stats.norm.sf(abs(z))


def tramos(s, centinela=None):
    """Etiqueta cada fila por tramo para graficar la tasa del objetivo: NA y centinela propios, un tramo por valor si la
    variable tiene <= 12 valores (cola rara agrupada), y deciles de los positivos (>= 100 filas por tramo) si no.
    Devuelve (serie de etiquetas, orden de las etiquetas)."""
    out = pd.Series("NA", index=s.index, dtype=object)
    neg = (s == centinela) if centinela is not None else pd.Series(False, index=s.index)
    ok = s.notna() & ~neg; v = s[ok]; out[neg] = str(centinela)
    orden = [l for l, hay in (("NA", (~ok & ~neg).any()), (str(centinela), neg.any())) if hay]
    if v.nunique() <= 12:
        cuentas = v.value_counts().sort_index(); tope = cuentas[cuentas >= 50].index.max()
        for x in cuentas.index[cuentas.index < tope]:
            lab = f"{x:g}"; out[ok & (s == x)] = lab; orden.append(lab)
        lab = f"≥{tope:g}"; out[ok & (s >= tope)] = lab; orden.append(lab)
    else:
        if (v == 0).any(): out[ok & (s == 0)] = "0"; orden.append("0")
        pos = ok & (s > 0); nb = min(10, int(pos.sum()) // 100)
        if nb <= 1:
            out[pos] = ">0"; orden.append(">0")
        else:
            q = pd.qcut(s[pos], nb, duplicates="drop")
            for itv in q.cat.categories:
                lab = f"≤{itv.right:.3g}"; out[pos & (s > itv.left) & (s <= itv.right)] = lab; orden.append(lab)
    return out, orden
