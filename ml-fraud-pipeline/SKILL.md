---
name: ml-fraud-pipeline
description: >-
  Crea y desarrolla de punta a punta un proyecto de ML de detección de fraude en transacciones (o de riesgo con
  objetivo binario desbalanceado): arquitectura del repositorio, EDA, capa de features con dbt, stage processor,
  torneo de modelos con validación cruzada anidada, inference, recomendaciones de prevención, DAG de Airflow,
  Terraform (S3, IAM, Glue, SageMaker, EC2) e informe en Word, aplicando buenas prácticas y puertas de calidad en cada
  etapa (sin fuga de información, pruebas de datos, verificaciones independientes, honestidad sobre límites). Úsala
  siempre que el usuario quiera replicar este desarrollo, montar un pipeline de fraude o de scoring de riesgo, escribir
  un EDA para fraude, construir features con dbt para un modelo, comparar clasificadores sobre datos desbalanceados,
  pasar un modelo de un notebook a producción (dbt + Airflow + SageMaker), o revisar que un proyecto así cumpla buenas
  prácticas, aunque no mencione todas las etapas ni la palabra «fraude».
---

# Pipeline de ML para detección de fraude en transacciones

Este skill guía la construcción de un proyecto completo, con la misma arquitectura y disciplina con las que se
desarrolló una prueba técnica de detección de fraude. Cada etapa tiene **plantillas probadas**, una **referencia** con el
porqué de cada práctica y una **puerta de calidad**: no se pasa a la etapa siguiente sin superarla.

## Cómo trabajar

- **Hazlo con el usuario, no por él.** El usuario debe poder explicar cada decisión (suele ser para una entrevista o una
  auditoría). Explica el porqué de cada paso y registra las decisiones.
- **No pises su trabajo.** Si el usuario ya tiene cuadernos, SQL o informes, inserta o modifica celdas concretas; no
  regeneres archivos que él edita. Haz una copia de seguridad (fuera del repositorio) antes de modificar algo suyo.
- **Pide permiso para instalar o confirmar.** Instalar paquetes del sistema (p. ej. `brew install libomp`), crear
  repositorios remotos, hacer commit o push son acciones que el usuario debe autorizar; los cambios pendientes que él
  tenga sin confirmar no se confirman en su nombre.
- **Cada cifra sale de código ejecutado.** Antes de escribir una conclusión, contrástala con la salida real. Lo que no se
  puede verificar se marca como hipótesis. Esto evita informes con cifras de análisis que ya no existen.
- **Lo que no se ejecutó, se dice.** Un DAG verificado con un Airflow simulado o una infraestructura que solo pasó
  `terraform validate` no es un despliegue probado: decláralo en el informe y en los README.
- **Trazabilidad opcional pero recomendada.** Si el usuario quiere mostrar cómo usó IA, lleva una bitácora de pasos, los
  prompts (original y refinado) y las decisiones con sus alternativas.

## Flujo y puertas de calidad

```
datos crudos ─► dbt (stg → int → mart + pruebas) ─► processor ─► tournament ─► inference ─► recommended
                       └──────────── Airflow (DAG diario, torneo semanal) · Terraform (AWS) ────────────┘
```

| Fase | Entregable | Plantilla (`assets/templates/`) | Lee antes | Puerta de calidad |
|---|---|---|---|---|
| 0 | Decisiones del caso | — | `references/00-principios.md` | Respuestas del usuario registradas |
| 1 | Arquitectura del repo | `base/`, todo vía `scripts/scaffold.py` | `01-arquitectura-repo.md` | `verificar_proyecto.py` sin FALLAS |
| 2 | EDA con conclusiones | `eda/helpers.py` | `02-eda.md` | Cada cifra de las conclusiones sale de una celda; cuaderno corre de arriba abajo |
| 3 | Capa dbt | `dbt/` | `03-dbt.md` | `dbt build` verde, paridad con pandas, prueba negativa |
| 4 | Stage processor | `ml/__MODELO__/processor/` | `04-processor.md` | Partición = la del EDA; preprocesador aprende solo de train |
| 5 | Torneo | `ml/__MODELO__/tournament/` | `05-tournament.md` | Protocolo anidado; test usado una vez; honestidad sobre la búsqueda |
| 6 | Inference y recommended | `ml/__MODELO__/{inference,recommended}/` | `06-inference-recommended.md` | `inference` reproduce la métrica del torneo |
| 7 | DAG e IaC | `airflow/`, `iac/` | `07-airflow-iac.md` | `verificar_dag.py` y `terraform validate`; límites declarados |
| 8 | Informe | `informe/informe_base.js` | `08-informe.md` | Revisión visual de cada página; cifras verificadas |
| 9 | Cierre | — | `09-errores-comunes.md` | `verificar_proyecto.py` limpio; ramas y PRs |

Lee solo la referencia de la fase en la que estás: cada una es independiente.

## Fase 0 — Entender el caso

Pregunta (y registra) antes de generar nada, porque cambian el diseño:

1. ¿Cuál es la **unidad** (transacción, cuenta, usuario), el **objetivo** (columna y definición) y la **prevalencia**?
2. ¿Hay **variable temporal**? Si no, no hay backtesting fuera de tiempo: se usa validación cruzada estratificada y se
   declara como limitación. Si la hay, la partición y la validación deben ser temporales.
3. ¿Qué **algoritmos** se pueden usar y cuántos se esperan comparar? (por defecto: regresión logística, Random Forest,
   XGBoost y LightGBM)
4. ¿Hay **variables anónimas o sospechosas** (que podrían ser fuga o artefactos del muestreo)? Se evalúan con y sin.
5. **Plataforma**: AWS (Athena/Glue/SageMaker) o GCP (BigQuery/Vertex); cambia el adaptador de dbt y la IaC.
6. **Datos confidenciales**: nunca versionarlos; repositorio privado; el CSV queda fuera de Git.
7. **Entregable final**: formato del informe (Word, PDF, PPT) y qué secciones exige.

## Fase 1 — Arquitectura del repositorio

```bash
python scripts/scaffold.py --destino <ruta> --proyecto <nombre-kebab> [--modelo <paquete>] [--componentes ...]
```

Crea `dbt/`, `ml/<modelo>/{processor,tournament,inference,recommended}`, `airflow/`, `iac/`, `src/eda/`, `reports/`,
`.gitignore`, `requirements.txt` y `README.md`, sustituyendo los marcadores `__PROYECTO__`, `__PROYECTO_SNAKE__` y
`__MODELO__`. No sobrescribe archivos existentes (usa `--simular` para ver qué haría). Después crea el repositorio
remoto (privado) y el flujo de ramas `feature → dev → release → main` si el usuario lo autoriza. Detalle en
`references/01-arquitectura-repo.md`.

## Fase 2 — EDA

Trabaja siempre **después** de separar test y solo sobre train. Sigue los 9 pasos de `references/02-eda.md`
(carga y partición, calidad, objetivo, faltantes, univariado, categórico, relación con el objetivo y entre variables,
discretas, conclusiones) con las funciones de `eda/helpers.py`. Para cada paso: tabla o gráfico, **conclusión con cifras de
la salida**, y decisión de preprocesamiento que se deriva. Reglas que evitan los errores más caros: no convertir con
`errors='coerce'` sin comprobar que no se crean NaN, no imputar ni partir por posición si el archivo viene ordenado, no
eliminar outliers sin comprobar si la cola es la señal, y no descartar variables por un test monótono si puede haber
relación en U.

## Fase 3 — dbt

dbt hace solo lo que **no aprende de los datos** (tipado, centinelas, indicadores, topes fijos, agrupaciones con listas
fijas, `log1p`) y las pruebas de calidad. Todo lo que usa estadísticas del conjunto completo va en el `processor`.
Desarrolla con DuckDB leyendo el CSV; el SQL es el mismo en producción. Puerta: `dbt build` verde, **paridad** del mart
con una implementación independiente en pandas, y una **prueba negativa** (datos corruptos deben hacer fallar las pruebas
y detener los modelos posteriores). Detalle y trampas en `references/03-dbt.md`.

## Fase 4 — processor

Parte train/test (estratificado, semilla fija) con **la misma partición del EDA** y define los preprocesadores por familia
(lineal y árboles), con y sin el grupo de variables sospechosas. Se ajustan solo con train y, en validación cruzada, dentro
del `Pipeline`. Comprueba que la mediana aprendida es la de train y no la de todo el conjunto. `references/04-processor.md`.

## Fase 5 — Torneo

Validación cruzada **anidada** para elegir, reajuste con todo train y **una sola** evaluación en test solo para reportar.
Métrica principal PR-AUC (la línea base es la prevalencia). Antes de la corrida completa, ejecuta `--rapido` (prueba de
humo). Cuando el campeón gane por poco, mira las diferencias **pareadas por fold** y compara contra el modelo con
hiperparámetros por defecto: si la búsqueda aporta poco, dilo. `references/05-tournament.md`.

## Fase 6 — Inference y recommended

`inference` carga el Pipeline completo, valida el esquema y la versión del modelo, y **debe reproducir exactamente la
métrica de test del torneo** (si no, algo está mal guardado). `recommended` convierte el score en acciones por bandas con
umbrales calculados con predicciones **fuera de muestra** de train (nunca con test), más motivos por operación. No inventes
costos de negocio: si no existen, usa precisiones objetivo y deja la política basada en costos como siguiente paso.
`references/06-inference-recommended.md`.

## Fase 7 — Airflow e IaC

DAG diario que encadena dbt (con pruebas), processor, torneo (semanal, con rama), inference y recommended; los módulos de
ML como SageMaker Processing jobs. Terraform: buckets de S3 (versionado, cifrado, acceso público bloqueado, ciclo de vida;
los modelos no expiran), IAM de mínimo privilegio, Glue, registro de modelos y recursos de pago **opcionales y apagados por
defecto**. Verifica con `airflow/tests/verificar_dag.py` y `terraform validate`; no declares más de lo verificado.
`references/07-airflow-iac.md`.

## Fase 8 — Informe

Estructura que responde a lo que suele pedir un ejercicio: resumen (aproximación, hipótesis, resultado y estrategia de
prevención), datos, metodología, EDA, features, entrenamiento paso a paso, resultados y comparación, modelo elegido y por
qué, producción, limitaciones y trabajo futuro. Genera figuras desde el estado ejecutado, construye el `.docx` con
`informe/informe_base.js`, valídalo, expórtalo a PDF y **revisa visualmente cada página**. `references/08-informe.md`.

## Fase 9 — Cierre

```bash
python scripts/verificar_proyecto.py <ruta-del-proyecto>
```

Es una revisión **estática** de buenas prácticas (estructura, `.gitignore`, secretos, pruebas de dbt, ausencia de ajuste
sobre test, DAG, controles de S3…). Corrige las FALLAS y justifica los AVISOS. Luego abre los pull requests en el orden del
flujo de ramas, si el usuario lo pide. Repasa `references/09-errores-comunes.md` como lista final.

## Qué no hacer

- No entrenar ni decidir nada con test; no usar `accuracy` como métrica principal con clases desbalanceadas.
- No calcular medianas, cuantiles ni frecuencias sobre todo el conjunto antes de partir (ni en dbt ni en pandas).
- No dar por buena una cifra sin la celda que la produce, ni un resultado sin compararlo con una referencia (línea base,
  modelo por defecto, implementación independiente).
- No presentar simulaciones (DAG, IaC) como despliegues; no versionar datos, estados de Terraform ni modelos.
