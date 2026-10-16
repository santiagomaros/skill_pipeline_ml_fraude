"""Verifica la estructura del DAG sin Airflow instalado: sustituye `airflow` por clases mínimas que registran las
tareas y sus dependencias, importa el DAG y comprueba que el grafo es el esperado.

Uso (desde la raíz del proyecto):  python airflow/tests/verificar_dag.py
Esto NO prueba la ejecución real en Airflow ni en SageMaker.
"""
import importlib.util
import sys
import types
from pathlib import Path

TAREAS: dict[str, "Tarea"] = {}


class Tarea:
    def __init__(self, task_id, **kw):
        self.task_id, self.kw, self.aguas_abajo = task_id, kw, set()
        TAREAS[task_id] = self

    def __rshift__(self, otro):
        for destino in (otro if isinstance(otro, list) else [otro]):
            self.aguas_abajo.add(destino.task_id)
        return otro

    def __rrshift__(self, otros):                    # lista >> tarea
        for origen in otros:
            origen.aguas_abajo.add(self.task_id)
        return self


class DAG:
    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self): return self
    def __exit__(self, *a): return False


def _modulo(nombre, **atributos):
    m = types.ModuleType(nombre)
    m.__dict__.update(atributos)
    sys.modules[nombre] = m
    return m


class Variable:
    @staticmethod
    def get(clave, default_var=None): return default_var


for nombre, clase in [("airflow.operators.bash", "BashOperator"), ("airflow.operators.empty", "EmptyOperator"),
                      ("airflow.operators.python", "BranchPythonOperator"),
                      ("airflow.providers.amazon.aws.operators.glue_crawler", "GlueCrawlerOperator"),
                      ("airflow.providers.amazon.aws.operators.sagemaker", "SageMakerProcessingOperator")]:
    _modulo(nombre, **{clase: type(clase, (Tarea,), {})})
_modulo("airflow", DAG=DAG)
_modulo("airflow.models", Variable=Variable)

ruta = Path(__file__).resolve().parents[1] / "dags" / "__PROYECTO_SNAKE___diario.py"
spec = importlib.util.spec_from_file_location("__PROYECTO_SNAKE___diario", ruta)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

esperado = {
    "dbt_build": {"publicar_features_s3"}, "publicar_features_s3": {"crawler_glue"}, "crawler_glue": {"processor"},
    "processor": {"es_dia_de_torneo"}, "es_dia_de_torneo": {"torneo", "omitir_torneo"},
    "torneo": {"inference"}, "omitir_torneo": {"inference"}, "inference": {"recommended"},
    "recommended": {"fin"}, "fin": set(),
}
real = {k: t.aguas_abajo for k, t in TAREAS.items()}
assert real == esperado, f"grafo distinto al esperado:\n{real}"
assert TAREAS["inference"].trigger_rule == "none_failed_min_one_success"
for tarea in ("processor", "torneo", "inference", "recommended"):
    cfg = TAREAS[tarea].kw["config"]
    assert cfg["AppSpecification"]["ContainerEntrypoint"][:2] == ["python", "-m"]
    assert cfg["ProcessingResources"]["ClusterConfig"]["InstanceType"].startswith("ml.")
from datetime import datetime  # la rama elige torneo solo los lunes (2026-10-12 es lunes)
assert mod.elegir_rama(datetime(2026, 10, 12)) == "torneo" and mod.elegir_rama(datetime(2026, 10, 13)) == "omitir_torneo"
print(f"DAG correcto: {len(TAREAS)} tareas, grafo y reglas verificados")
