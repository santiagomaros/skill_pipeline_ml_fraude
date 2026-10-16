# Principios transversales

Estas reglas se aplican en todas las fases. Cada una existe porque su ausencia produjo un error real.

## 1. Sin fuga de información (leakage)

- **Parte primero, explora después.** La partición train/test (estratificada, semilla fija) va antes del EDA; todo el
  análisis usa solo train. Test se usa **una vez**, al final, y solo para reportar.
- **Lo que se aprende de los datos vive dentro del `Pipeline`** (mediana, cuartiles, escalado, one-hot, selección). En
  validación cruzada se reajusta en cada fold. Comprobación concreta: la mediana que aprende el preprocesador debe ser la de
  train, no la de todo el conjunto.
- **Nada con estadísticas del conjunto completo en dbt** (medianas, cuantiles, frecuencias, la etiqueta). dbt solo hace lo
  que no aprende de los datos.
- **Datos ordenados.** Si el archivo viene ordenado (p. ej. por clase), nunca partir, muestrear ni imputar por posición
  (`head`, `iloc`, `bfill`, `ffill`). Comprueba el orden en el paso de partición.
- **Disponibilidad al decidir.** Una variable muy predictiva y anónima puede calcularse *después* de la decisión. Pregunta al
  dueño de los datos y deja la hipótesis escrita.

## 2. Qué va en dbt y qué en el processor

| dbt (sin estado, parámetros fijos) | processor (aprende de train) |
|---|---|
| Tipado y limpieza; indicadores de faltante, de centinela y `x > 0`; topes fijos; agrupación con **lista fija**; `log1p` | Imputación, escalado, cuartiles, codificadores, partición, validación cruzada |

Los parámetros fijos (listas de categorías, topes) salen del EDA hecho **sobre train** y se escriben como constantes en
`dbt_project.yml`: no se recalculan en SQL.

## 3. Cifras verificables

- Cada número de una conclusión sale de una celda o script ejecutado. Si se retira un análisis del cuaderno, se retiran sus
  cifras de las conclusiones, del resumen y del informe (revisa la lista tras cada recorte).
- Contrasta siempre con una referencia: línea base (prevalencia), modelo por defecto, implementación independiente.
- Lo que no se puede verificar (variables anónimas, supuestos) se marca como **hipótesis**, con su evidencia y estado.

## 4. Verificación independiente (barata y muy rentable)

- **Paridad:** reimplementa en pandas la capa de dbt y compara conteos, sumas y valores. Detecta errores de tipo y de lógica.
- **Reproducción:** `inference` debe devolver exactamente la métrica de test que reportó el torneo.
- **Prueba negativa:** corrompe datos a propósito y comprueba que las pruebas fallan y que lo posterior no se ejecuta.
- **Prueba de humo:** corre el torneo en modo rápido antes de la corrida completa.
- **Un resultado absurdo se investiga** (un PSI de 13,8 era un error de cortes, no deriva).

## 5. Criterios propios del fraude

- Métrica principal **PR-AUC** (línea base = prevalencia) acompañada de ROC-AUC, F1 máximo, recall a precisión fija y Brier;
  *accuracy* no sirve con clases desbalanceadas.
- **Faltantes, centinelas (-1) y valores extremos suelen ser señal**, no ruido: estúdialos antes de imputar o recortar.
- **Los tests monótonos no ven relaciones en U** (una variable puede tener AUC ≈ 0,5 y una relación fuerte): complementa
  con chi-cuadrado/tendencia por niveles y gráficos por tramos.
- **Etiquetas en producción:** llegan tarde (contracargos), se censuran (lo rechazado no tiene etiqueta) y cambian por
  adaptación del defraudador; documenta cómo se manejarán antes de prometer métricas de producción.
- **Calibración:** si se fijan umbrales sobre el score, comprueba que la probabilidad media por decil coincide con la tasa
  observada.

## 5b. Honestidad

- Declara lo que **no** se ejecutó (Airflow real, `terraform plan/apply`), las limitaciones (sin variable temporal,
  prevalencia de la muestra distinta de la real) y los hallazgos que debilitan la narrativa (p. ej., la búsqueda de
  hiperparámetros aportó +0,003 sobre los valores por defecto).
- No uses una frase como «mismo criterio» si los presupuestos de cómputo difieren entre modelos.

## 6. Colaboración

- Copia de seguridad (fuera del repositorio) antes de tocar archivos del usuario; modifica solo lo pedido y avisa de lo
  que veas roto en el resto, sin arreglarlo en silencio.
- Pide permiso para instalar paquetes, dependencias del sistema, crear repositorios o hacer commit/push.
- Ejecuta el cuaderno **de arriba abajo en un kernel limpio** antes de afirmar que funciona: los errores de orden de celdas
  (una celda que usa una variable definida más abajo) solo aparecen así.
