# skill_pipeline_ml_fraude

Skill para **Claude Code** que guía la construcción, de punta a punta, de un proyecto de ML para **detección de fraude en
transacciones** (o de cualquier objetivo binario desbalanceado, como riesgo de crédito o abuso), con la misma arquitectura y
disciplina de una prueba técnica de ML Engineer: **EDA → dbt → processor → torneo de modelos → inference → recommended →
Airflow → Terraform → informe**, con buenas prácticas y una puerta de calidad en cada etapa.

El skill se llama `ml-fraud-pipeline` y vive en [`ml-fraud-pipeline/`](ml-fraud-pipeline/).

## Qué hace

Cuando el usuario pide replicar este desarrollo o montar un pipeline parecido, el skill:

1. **Pregunta lo que cambia el diseño** (unidad, objetivo, prevalencia, variable temporal, algoritmos permitidos, plataforma,
   confidencialidad, entregable).
2. **Crea la arquitectura del repositorio** con un script (`scaffold.py`) y plantillas ya probadas.
3. **Guía cada etapa** con su porqué, sus trampas conocidas y una **puerta de calidad** que hay que superar antes de seguir.
4. **Verifica** el resultado con una revisión estática de buenas prácticas (`verificar_proyecto.py`).

| Etapa | Qué incluye | Buena práctica que garantiza |
|---|---|---|
| EDA | Protocolo de 9 pasos, tests por la forma de los datos, `helpers.py` | Solo train, cifras verificables, faltantes y extremos como señal, tests no monótonos complementados |
| dbt | stg → int → mart, macros, pruebas genéricas, singulares y unitaria | Solo transformaciones sin estado (sin fuga), paridad con pandas, prueba negativa |
| processor | Partición y preprocesadores por familia, con y sin variable sospechosa | La misma partición del EDA; todo se aprende solo de train |
| tournament | Validación cruzada anidada, 4 algoritmos, métricas para desbalance | Test usado una vez; honestidad sobre el aporte de la búsqueda |
| inference | Pipeline completo, validación de esquema, versión del modelo | Reproduce la métrica de test del torneo |
| recommended | Política por bandas con umbrales fuera de muestra, motivos por operación | Umbrales sin tocar test; sin costos inventados |
| Airflow | DAG diario con torneo semanal y verificador de estructura | Si fallan las pruebas de dbt no se puntúa; límites declarados |
| Terraform | S3 (versionado, cifrado, ciclo de vida), IAM, Glue, registro de modelos, EC2/endpoint opcionales | Mínimo privilegio; recursos de pago apagados por defecto |
| Informe | Constructor Word (docx-js) y guía de revisión | Revisión visual y consistencia con el cuaderno |

## Casos de uso

1. **Replicar una prueba técnica de fraude de punta a punta**: «tengo un CSV de operaciones con una columna de fraude y
   necesito entrenar y comparar al menos tres algoritmos, elegir uno y justificarlo».
2. **Montar la arquitectura de un nuevo proyecto de scoring** con dbt, SageMaker y Airflow (fraude, riesgo, abuso,
   abandono), partiendo de un esqueleto que ya corre.
3. **Auditar un proyecto existente**: pasar `verificar_proyecto.py` y repasar la lista de errores comunes (fuga de
   información, datos versionados, DAG sin reintentos, buckets sin cifrado…).
4. **Desarrollar solo una etapa**: únicamente el EDA para fraude, únicamente la capa dbt con sus pruebas, o únicamente el
   torneo con validación anidada.
5. **Pasar un notebook a producción**: separar qué va en dbt y qué en el processor, y llevarlo a un pipeline orquestado.
6. **Preparar el informe o la presentación** de una prueba técnica, con estructura, figuras y revisión visual.
7. **Preparar una entrevista técnica** sobre el proyecto: cada decisión viene con su porqué y sus alternativas.
8. **Adaptar a otra plataforma**: cambiar el adaptador de dbt y los recursos de la IaC (p. ej., BigQuery y Vertex AI).

## Instalación

Copia la carpeta del skill a donde Claude Code busca skills:

```bash
# personal (todos tus proyectos)
cp -r ml-fraud-pipeline ~/.claude/skills/

# o solo para un proyecto
mkdir -p <proyecto>/.claude/skills && cp -r ml-fraud-pipeline <proyecto>/.claude/skills/
```

Reinicia la sesión de Claude Code. El skill se activa solo cuando la tarea encaja con su descripción; también puedes pedirlo
por su nombre.

## Cómo usarlo (ejemplos de peticiones)

- «Usa el skill ml-fraud-pipeline para crear la arquitectura de un proyecto de detección de fraude llamado `fraude-pagos`.»
- «Ayúdame con el EDA de este dataset de fraude: ya separé train y test.»
- «Revisa si mi proyecto cumple las buenas prácticas del pipeline de fraude.»
- «Genera la capa dbt de features para estas decisiones del EDA y verifícala contra pandas.»

Scripts incluidos (requieren Python 3.10+):

```bash
python ml-fraud-pipeline/scripts/scaffold.py --destino ~/proyectos/fraude-pagos --proyecto fraude-pagos
python ml-fraud-pipeline/scripts/verificar_proyecto.py ~/proyectos/fraude-pagos
```

## Estructura

```
ml-fraud-pipeline/
├── SKILL.md                      flujo, fases y puertas de calidad (lo que Claude lee al activarse)
├── references/                   una guía por fase (00 principios … 09 errores comunes)
├── scripts/
│   ├── scaffold.py               crea la arquitectura desde las plantillas
│   └── verificar_proyecto.py     revisión estática de buenas prácticas
└── assets/templates/             base · dbt · ml · airflow · iac · eda · informe
```

## Qué se probó y qué no

- Las plantillas se **ejecutaron de punta a punta con datos sintéticos**: `scaffold.py` → `dbt build` (11/11 entre modelos y pruebas) →
  processor → torneo (fase 1 y 2) → inference (reproduce la métrica del torneo) → recommended. Las contribuciones exactas por
  operación se comprobaron para LightGBM, XGBoost y regresión logística; Random Forest usa un respaldo documentado.
- `verificar_proyecto.py` se comprobó en positivo (proyecto real y plantilla) y en negativo (proyecto roto).
- El DAG se verifica por estructura con un Airflow simulado y la IaC con `terraform validate`: **no se ejecutaron en un
  Airflow ni en una cuenta de AWS real**.
- **No se ejecutó una evaluación comparativa del skill** (con y sin skill sobre varias tareas): el siguiente paso natural es
  probarlo en un proyecto nuevo y ajustar `SKILL.md` con lo que se observe.

## Alcance y límites

- Pensado para **datos tabulares con objetivo binario desbalanceado**; no cubre modelos de grafos, secuencias ni tiempo real
  con latencia estricta (se mencionan como siguientes pasos).
- Las plantillas asumen Python con pandas/scikit-learn, dbt con DuckDB para desarrollo, y AWS para producción.
- Los parámetros de las plantillas (listas de columnas, topes, categorías) son marcadores `TODO` que salen del EDA de cada
  proyecto: el skill no trae decisiones de ningún dataset concreto.

## Origen

Derivado de una prueba técnica de detección de fraude en transacciones. No contiene datos ni enunciados del proceso de
selección: solo el método, las plantillas genéricas y las lecciones aprendidas.
