#!/usr/bin/env python3
"""Crea la arquitectura de un proyecto de detección de fraude a partir de las plantillas del skill.

Ejemplo:
    python scaffold.py --destino ~/proyectos/fraude-pagos --proyecto fraude-pagos [--modelo modelo_fraude_pagos]
                       [--componentes base dbt ml airflow iac eda informe] [--forzar] [--simular]

Sustituye los marcadores __PROYECTO__ (kebab-case), __PROYECTO_SNAKE__ y __MODELO__ en rutas y contenidos.
No sobrescribe archivos existentes salvo que se pase --forzar (así no pisa trabajo del usuario).
"""
import argparse
import re
import sys
from pathlib import Path

PLANTILLAS = Path(__file__).resolve().parents[1] / "assets" / "templates"
DESTINO_DE = {"base": ".", "dbt": "dbt", "ml": "ml", "airflow": "airflow", "iac": "iac", "eda": "src/eda", "informe": "reports"}


def snake(s):
    return re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()


def kebab(s):
    return re.sub(r"[^0-9a-zA-Z]+", "-", s).strip("-").lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--destino", required=True, type=Path)
    ap.add_argument("--proyecto", required=True, help="nombre del proyecto, p. ej. fraude-pagos")
    ap.add_argument("--modelo", help="nombre del paquete del modelo dentro de ml/ (por defecto modelo_<proyecto>)")
    ap.add_argument("--componentes", nargs="+", choices=list(DESTINO_DE), default=list(DESTINO_DE))
    ap.add_argument("--forzar", action="store_true", help="sobrescribe archivos existentes")
    ap.add_argument("--simular", action="store_true", help="solo muestra lo que haría")
    a = ap.parse_args()

    sust = {"__PROYECTO_SNAKE__": snake(a.proyecto), "__PROYECTO__": kebab(a.proyecto),
            "__MODELO__": snake(a.modelo or f"modelo_{snake(a.proyecto)}")}

    def aplicar(texto):
        for k, v in sust.items():
            texto = texto.replace(k, v)
        return texto

    creados, omitidos = [], []
    for comp in a.componentes:
        origen = PLANTILLAS / comp
        for f in sorted(p for p in origen.rglob("*") if p.is_file()):
            rel = Path(*[aplicar(parte) for parte in f.relative_to(origen).parts])
            destino = a.destino / DESTINO_DE[comp] / rel
            if destino.exists() and not a.forzar:
                omitidos.append(destino); continue
            creados.append(destino)
            if not a.simular:
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(aplicar(f.read_text()))
    print(f"{'(simulación) ' if a.simular else ''}creados: {len(creados)} | omitidos por existir: {len(omitidos)}")
    for d in creados:
        print("  +", d.relative_to(a.destino))
    for d in omitidos:
        print("  =", d.relative_to(a.destino), "(ya existe)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
