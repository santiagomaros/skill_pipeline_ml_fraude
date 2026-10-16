#!/usr/bin/env python3
"""Revisión estática de buenas prácticas de un proyecto de detección de fraude (arquitectura del skill ml-fraud-pipeline).

Uso:  python verificar_proyecto.py [RAIZ_DEL_PROYECTO]      (por defecto, el directorio actual)

Cada comprobación termina en OK, AVISO o FALLA. Es una red de seguridad barata: NO sustituye ejecutar el pipeline,
las pruebas de dbt ni revisar el informe. Código de salida 1 si hay alguna FALLA.
"""
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
IGNORAR = {".git", ".venv", "venv", "node_modules", ".terraform", "target", "__pycache__", "dbt_packages", "logs", ".ipynb_checkpoints", "artefactos"}
res = []


def registrar(estado, texto):
    res.append((estado, texto))


def archivos(patron):
    return [p for p in RAIZ.rglob(patron) if not (set(p.relative_to(RAIZ).parts) & IGNORAR)]


def leer(p):
    try:
        return p.read_text(errors="ignore")
    except OSError:
        return ""


# 1. Estructura ---------------------------------------------------------------------------------------------------
for d in ("dbt", "airflow", "iac", "ml"):
    registrar("OK" if (RAIZ / d).is_dir() else "FALLA", f"existe la carpeta {d}/")
modelos = [m for m in (RAIZ / "ml").glob("*") if m.is_dir() and (m / "processor").is_dir()] if (RAIZ / "ml").is_dir() else []
if modelos:
    for etapa in ("processor", "tournament", "inference", "recommended"):
        ok = all((m / etapa).is_dir() for m in modelos)
        registrar("OK" if ok else "FALLA", f"ml/{modelos[0].name}/{etapa}/")
else:
    registrar("FALLA", "ml/<modelo>/{processor,tournament,inference,recommended} no encontrado")

# 2. .gitignore y secretos ----------------------------------------------------------------------------------------
gi = leer(RAIZ / ".gitignore")
for patron, motivo in [("csv", "datos de entrada fuera de Git"), (".terraform", "caché de Terraform"), ("tfstate", "estado de Terraform"),
                       (".venv", "entorno virtual"), ("artefactos", "modelos y artefactos")]:
    registrar("OK" if patron in gi else "AVISO", f".gitignore cubre {patron} ({motivo})")
try:
    versionados = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True).stdout.split()
    csv = [f for f in versionados if f.lower().endswith((".csv", ".tfstate", ".joblib", ".pkl", ".duckdb"))]
    registrar("OK" if not csv else "FALLA", "no hay datos, estados o modelos versionados" + (f": {csv[:5]}" if csv else ""))
except FileNotFoundError:
    pass
patron_secretos = re.compile(r"AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=\s*\S+|BEGIN (RSA |EC )?PRIVATE KEY|password\s*=\s*['\"][^'\"]+['\"]", re.I)
hallazgos = [p.relative_to(RAIZ) for ext in ("*.py", "*.tf", "*.yml", "*.yaml", "*.sql", "*.sh", "*.md", "*.json") for p in archivos(ext)
             if patron_secretos.search(leer(p)) and p.name != "verificar_proyecto.py"]
registrar("OK" if not hallazgos else "FALLA", "sin credenciales en el código" + (f": {hallazgos[:5]}" if hallazgos else ""))

# 3. Entorno -------------------------------------------------------------------------------------------------------
req = leer(RAIZ / "requirements.txt")
registrar("OK" if "==" in req else "AVISO", "requirements.txt con versiones fijadas (==)")

# 4. dbt -----------------------------------------------------------------------------------------------------------
sin_comentarios = lambda t: re.sub(r"--[^\n]*|/\*.*?\*/|\{#.*?#\}", "", t, flags=re.S)       # los comentarios no cuentan
sql_stg = " ".join(sin_comentarios(leer(p)) for p in archivos("*.sql") if "staging" in p.parts)
registrar("FALLA" if re.search(r"type_float\(\)", sql_stg) else "OK", "staging sin dbt.type_float() (FLOAT de 32 bits en DuckDB distorsiona importes; usar tipo_decimal())")
yml = " ".join(leer(p) for p in archivos("*.yml") if "dbt" in p.parts)
registrar("OK" if re.search(r"data_tests|tests:", yml) else "FALLA", "dbt: pruebas genéricas definidas en los .yml")
registrar("OK" if any(p for p in archivos("*.sql") if "tests" in p.parts) else "FALLA", "dbt: pruebas singulares en tests/")
registrar("OK" if "unit_tests" in yml else "AVISO", "dbt: al menos una prueba unitaria (unit_tests)")
mart_sql = " ".join(sin_comentarios(leer(p)) for p in archivos("*.sql") if "marts" in p.parts or "intermediate" in p.parts)
registrar("FALLA" if re.search(r"\b(avg|median|percentile_cont|ntile|stddev)\s*\([^)]*\)\s*over\s*\(\s*\)", mart_sql, re.I) else "OK",
          "dbt: sin estadísticas del dataset completo (avg/median/ntile sobre toda la tabla) en int/marts (serían fuga)")

# 5. ML ------------------------------------------------------------------------------------------------------------
py_ml = [p for p in archivos("*.py") if "ml" in p.relative_to(RAIZ).parts[:1]]
texto_ml = {p: leer(p) for p in py_ml}
todo = "\n".join(texto_ml.values())
registrar("OK" if "stratify" in todo and "random_state" in todo else "FALLA", "ml: partición estratificada con semilla fija")
registrar("OK" if "Pipeline" in todo else "FALLA", "ml: preprocesadores dentro de un Pipeline (se reajustan en cada fold)")
registrar("OK" if "RandomizedSearchCV" in todo and "cross_validate" in todo else "AVISO", "ml: validación cruzada anidada (búsqueda dentro de cross_validate)")
malo = [p.name for p, t in texto_ml.items() if re.search(r"\.fit(_transform)?\(\s*X_te|\.fit(_transform)?\(\s*test", t) or re.search(r"\b(bfill|ffill)\(", t)]
registrar("OK" if not malo else "FALLA", "ml: sin ajustar sobre test ni bfill/ffill (los datos pueden venir ordenados)" + (f": {malo}" if malo else ""))
registrar("OK" if any(("feature_names_in_" in t) for t in texto_ml.values()) else "AVISO", "inference: valida el esquema de entrada")
registrar("OK" if any(("sha256" in t or "modelo_version" in t) for t in texto_ml.values()) else "AVISO", "inference: cada score lleva la versión del modelo")
registrar("OK" if "average_precision" in todo or "pr_auc" in todo else "AVISO", "ml: métrica principal adecuada al desbalance (PR-AUC)")

# 6. Airflow -------------------------------------------------------------------------------------------------------
dags = [p for p in archivos("*.py") if "dags" in p.parts]
registrar("OK" if dags else "FALLA", "airflow: existe al menos un DAG")
if dags:
    t = "\n".join(leer(p) for p in dags)
    registrar("OK" if "catchup=False" in t else "AVISO", "airflow: catchup=False")
    registrar("OK" if "retries" in t else "AVISO", "airflow: reintentos definidos")
    registrar("OK" if any("verificar_dag" in p.name for p in archivos("*.py")) else "AVISO", "airflow: prueba de estructura del DAG")

# 7. Terraform -----------------------------------------------------------------------------------------------------
tf = "\n".join(leer(p) for p in archivos("*.tf"))
for recurso, motivo in [("aws_s3_bucket_public_access_block", "acceso público bloqueado"), ("aws_s3_bucket_server_side_encryption_configuration", "cifrado"),
                        ("aws_s3_bucket_versioning", "versionado"), ("aws_s3_bucket_lifecycle_configuration", "ciclo de vida")]:
    registrar("OK" if recurso in tf else "FALLA" if tf else "AVISO", f"iac: S3 con {motivo}")
registrar("OK" if (RAIZ / "iac" / ".terraform.lock.hcl").exists() else "AVISO", "iac: .terraform.lock.hcl versionado (ejecutar terraform init)")

# ---------------------------------------------------------------------------------------------------------------
simbolo = {"OK": "[OK]    ", "AVISO": "[AVISO] ", "FALLA": "[FALLA] "}
for estado, texto in res:
    print(simbolo[estado], texto)
n = {e: sum(1 for x, _ in res if x == e) for e in ("OK", "AVISO", "FALLA")}
print(f"\n{n['OK']} OK · {n['AVISO']} avisos · {n['FALLA']} fallas   (revisión estática: no sustituye ejecutar pruebas ni revisar el informe)")
sys.exit(1 if n["FALLA"] else 0)
