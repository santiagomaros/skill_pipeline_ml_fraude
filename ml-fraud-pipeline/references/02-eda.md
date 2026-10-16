# EDA para fraude: protocolo, tests y trampas

Todo el EDA se calcula sobre **train**. Cada paso termina con una **conclusión que cita cifras de su salida** y con la
decisión de preprocesamiento que habilita. Las funciones de apoyo están en `assets/templates/eda/helpers.py`.

## Pasos

| # | Paso | Qué hacer | Test / técnica |
|---|---|---|---|
| 0 | Carga | Leer con el separador de miles correcto; **verificar que no se crean NaN** al tipar | Comparar NaN leídos con vacíos del archivo |
| 1 | Partición | 80/20 estratificada, semilla fija; comprobar si el archivo está **ordenado** | Tasa del objetivo en las primeras filas |
| 2 | Calidad | Duplicados, tipos, rangos, negativos, **centinelas** (-1, 999…), variables casi constantes, **ceros por variable** | Tabla de centinelas y de ceros con tasa del objetivo |
| 3 | Objetivo | Prevalencia, razón de desbalance, línea base de PR-AUC | Proporción (IC de Wilson) |
| 4 | Faltantes | % por columna; ¿el faltante se asocia con el objetivo?; ¿depende de otras variables? | χ² de independencia «falta ↔ objetivo» (decir si se rechaza H0) |
| 5 | Univariado numérico | Asimetría, curtosis, % ceros, colas; ¿el extremo es ruido o señal? | Tasa del objetivo en la cola > p99 vs resto (χ²); Q-Q (no Shapiro con n grande) |
| 6 | Categórico | Frecuencia, tasa por categoría, categorías raras y no vistas | χ² + V de Cramér; revisar celdas esperadas < 5 |
| 7 | Numéricas vs objetivo y entre sí | AUC univariada, Spearman, gráfico por tramos; correlograma | Mann-Whitney (AUC) + Benjamini-Hochberg; Spearman |
| 8 | Discretas | ¿numérica monótona o categórica? | χ² global + tendencia de Cochran-Armitage; tasa por nivel |
| 9 | Conclusiones | Ficha por variable (tratamiento y señal) y tabla de decisiones con su evidencia | — |

## Reglas de interpretación

- **Tamaño del efecto sobre p-valor.** Con n ≈ 10⁴ casi todo es significativo: reporta AUC, V de Cramér, tasas con IC.
- **Múltiples variables → corrección de Benjamini-Hochberg** (`scipy.stats.false_discovery_control`).
- **Los tests monótonos no ven la U.** Si una variable tiene AUC ≈ 0,5 pero el χ² por niveles es muy significativo, es no
  monótona: tratarla como categórica o dejarla a los árboles. Ejemplo típico: `Monto` en U invertida.
- **Variables inflacionadas de ceros** (≥ ~80% de ceros): `log1p` ayuda poco porque el problema es la masa en cero. Crea un
  indicador `x > 0` y conserva el valor para la parte positiva. Mira la tasa del objetivo con y sin cero antes de decidir
  (si casi no cambia, no hace falta indicador).
- **Centinelas y faltantes informativos:** conserva la señal con un indicador propio; no imputes a ciegas ni elimines la
  columna por tener muchos faltantes (la ausencia puede ser lo más informativo).
- **Outliers:** en fraude la cola suele ser la señal. No los elimines por regla (3-sigma, Tukey); mide primero la tasa del
  objetivo en la cola. La regla de Tukey no aplica si IQR = 0.
- **Categorías raras:** revisa la tasa de cada una **antes** de agruparlas (agrupar por frecuencia puede mezclar señales
  opuestas); reserva `OTRO` para lo realmente raro y envía allí las categorías no vistas. Cuidado con la separación casi
  perfecta (una categoría 100% objetivo y `OTRO` 0%) en modelos lineales: regulariza.
- **Imputación de una variable asimétrica:** mediana de train, con indicador de faltante, **en copias** (`train_imp`) si
  imputar distorsionaría los análisis posteriores de esa variable.
- **Normalidad:** no uses Shapiro con n grande (rechaza siempre); usa asimetría, curtosis y Q-Q.

## Hipótesis

Con variables anónimas, lo que no puede verificarse se escribe como `[H]` con evidencia y estado (plausible, no
confirmable, pendiente de confirmar con el dueño de los datos). Hipótesis habituales: el centinela significa «no
disponible»; una categoría con tasas extremas refleja el muestreo más que el riesgo; una variable es derivada de otras;
las variables más predictivas están disponibles en el momento de decidir. **No afirmes** como hecho que la muestra esté
enriquecida con fraudes si no puedes demostrarlo: di que la prevalencia de la muestra puede diferir de la de producción.

## Entregable del EDA

Un cuaderno que corre **de arriba abajo sin errores en un kernel limpio**, con la conclusión de cada paso, la tabla de
decisiones final y el alcance (qué análisis no se hicieron). Si el usuario quita un análisis, quita sus cifras de las
conclusiones.
