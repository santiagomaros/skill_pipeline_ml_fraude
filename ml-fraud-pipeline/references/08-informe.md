# Informe final

Pensado para un ejercicio que pide: paso a paso del entrenamiento de ≥ 3 algoritmos, enfoque e hipótesis, comparación de
rendimiento, qué modelo llevar a producción y por qué, y conclusiones. **Pregunta qué secciones quiere conservar el
usuario**: puede pedir quitar algunas (p. ej. el uso de IA o los anexos) o reducir las conclusiones; si quita algo que el
enunciado exige, adviértelo una vez y hazlo.

## Estructura recomendada

1. **Resumen ejecutivo:** aproximación al problema, resultado (tabla de modelos), hipótesis de trabajo, hallazgos y
   **estrategia de prevención** derivada de `recommended` (tabla de bandas), riesgos y estado de producción.
2. **Contexto, datos y objetivo** (tabla descriptiva, incluyendo variables inflacionadas de ceros).
3. **Aproximación y metodología:** principio rector orientado al fraude en transacciones (información disponible al decidir,
   desbalance, señal en faltantes/centinelas/extremos, validación sin variable temporal, tests por la forma de los datos).
4. **EDA e hipótesis:** calidad y objetivo (incluye la variable categórica y la categoría `OTRO`, y el indicador `x > 0`),
   faltantes, distribuciones, relación con el objetivo y **entre variables** (colinealidad, unida), hipótesis.
5. **Preparación de datos y features:** tabla «decisión del EDA → dónde (dbt/processor) → implementación».
6. **Entrenamiento paso a paso:** candidatos, *feature engineering* por familia, protocolo, búsqueda de hiperparámetros
   (con sus límites).
7. **Resultados y comparación:** tablas de Fase 1 y 2, figura, lectura.
8. **Modelo elegido y justificación**, con las alternativas descartadas y la advertencia sobre la variable sospechosa.
9. **Resultado de producción y recomendaciones** (política, resultado por acción, variables influyentes).
10. **Del notebook a producción:** dbt, Airflow, Terraform, y **qué se verificó y qué no**.
11. **Limitaciones, riesgos y próximos pasos.**
12. **Post-producción (aplicaciones futuras):** monitoreo, históricos de performance, reentrenamientos (solo enunciados si el
    usuario lo pide así).

## Cómo producirlo

- **Cifras:** del estado ejecutado (cuaderno, `torneo.json`, `recomendaciones.md`). Léelas en el script (JSON) en vez de
  transcribirlas para las tablas grandes; las demás, contrástalas con la salida.
- **Figuras:** un script (`reports/generar_figuras.py`) que ejecuta las celdas del cuaderno para reutilizar su estado y dibuja
  figuras compactas (anchos de 6–6,5 pulgadas, fuentes legibles). Si el cuaderno cambia, el script debe seguirlo (marcadores
  por texto de celda, tolerar celdas con dependencias fuera de orden).
- **Documento Word:** `informe/informe_base.js` (docx-js; `npm install docx`). Reglas de docx-js: tamaño de página explícito
  (carta), anchos en DXA en la tabla **y** en cada celda, `ShadingType.CLEAR`, listas con `numbering` (una referencia por
  lista para no continuar la numeración), `ImageRun` con `type`, nunca `\n` dentro de un párrafo.
- **Validación:** valida el OOXML (validador del skill `docx`), exporta a PDF (LibreOffice o, en macOS sin él, Pages por
  AppleScript) y **revisa visualmente cada página** (montajes de 6 páginas). Busca: páginas casi vacías por saltos de página,
  tablas partidas, listas numeradas que continúan, texto con marcas literales (`**`, `` ` ``), figuras ilegibles.
- **Marcado en línea:** el analizador de `**negrita**` no anida código; no pongas `` `código` `` dentro de negritas.

## Consistencia

- Tras quitar o fusionar secciones, repasa referencias cruzadas («sección 12», «Anexo A», etiquetas H1…H4) y la portada.
- Si el informe cita tests o análisis, comprueba que existen en el cuaderno (qué columnas se calculan y cuáles se muestran).
- Evita afirmar como hecho una hipótesis (p. ej. «la muestra está enriquecida»): usa «la prevalencia de la muestra puede
  diferir de la de producción».
