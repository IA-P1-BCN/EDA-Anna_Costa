# Informe de calidad de datos

**Datos:** The COVID Tracking Project, una fila por estado y día: 20.780 filas y 56 columnas de 56 estados y territorios, del 13-01-2020 al 07-03-2021.

Este informe recoge qué faltaba en los datos, qué se corrigió y qué quedó pendiente. Todas las cifras se calculan con `python -m src.informe_calidad` a partir de los originales; el detalle de cada decisión está en los notebooks 01, 02 y 06.

## Resumen

- **Qué faltaba:** se descartan 41 de las 56 columnas: vacías, constantes, repetidas, metadatos o con demasiados nulos. En las que se conservan, los nulos están casi siempre antes de que cada estado empezara a publicar y no se imputan.
- **Qué se corrigió:** 219 incrementos negativos pasan a `NaN` y los tests de 59 filas con más positivos que tests también. Los totales cambian un 0,03 % en casos y un 0,20 % en muertes.
- **Qué se marcó:** 183 atrasos de notificación, 640 días sin publicar y 126 filas incoherentes en columnas que no se usan.
- **Qué quedó pendiente:** las unidades distintas de los tests, los hospitalizados de la primavera de 2020 y los atrasos de varios días seguidos. Se explica por qué en el apartado 4.

## 1. Qué faltaba

### 1.1 Columnas descartadas

El original tiene 56 columnas. **24 están vacías en más de la mitad de las filas** y 2 no tienen ningún dato. No es un error de descarga: cada estado publicaba cosas distintas. Se conservan 15 columnas y se descartan 41:

| Motivo | Columnas | Cuáles |
| --- | --- | --- |
| Vacías al 100 % | 2 | `dataQualityGrade`, `grade` |
| Siempre valen 0 (la fuente las daba por obsoletas) | 5 | `commercialScore`, `negativeRegularScore`, `negativeScore`, `positiveScore`, `score` |
| Repiten otra columna | 3 | `total`, `posNeg`, `hospitalized` |
| Metadatos de la API (cuándo se actualizó el registro) | 5 | `hash`, `lastUpdateEt`, `dateModified`, `checkTimeEt`, `dateChecked` |
| Demasiados nulos o una unidad distinta en cada estado | 26 | `probableCases`, `negative`, `pending`, `hospitalizedCumulative`, `inIcuCumulative`, `onVentilatorCumulative`, `hospitalizedDischarged`, `totalTestsViral`, `positiveTestsViral`, `negativeTestsViral`, `positiveCasesViral`, `deathConfirmed`, `deathProbable`, `totalTestEncountersViral`, `totalTestsPeopleViral`, `totalTestsAntibody`, `positiveTestsAntibody`, `negativeTestsAntibody`, `totalTestsPeopleAntibody`, `positiveTestsPeopleAntibody`, `negativeTestsPeopleAntibody`, `totalTestsPeopleAntigen`, `positiveTestsPeopleAntigen`, `totalTestsAntigen`, `positiveTestsAntigen`, `negativeIncrease` |

Ninguna se imputa: en las columnas con más de la mitad de nulos habría que inventar más datos de los que hay. Del desglose de tests basta con `totalTestResults`, que ya junta los tests de cada estado, y `totalTestResultsSource`, que dice en qué unidad los contaba.

### 1.2 Nulos en las columnas que se conservan

Para cada columna, cuántos nulos caen **antes del primer dato** de cada estado (aún no publicaba, o no lo publicó nunca) y cuántos **después de empezar** (huecos o series que se cortan).

| Columna | % nulos | Antes del primer dato | Después de empezar | Decisión |
| --- | --- | --- | --- | --- |
| `fecha` | 0,0 % | 0 | 0 | Sin nulos |
| `estado` | 0,0 % | 0 | 0 | Sin nulos |
| `fips` | 0,0 % | 0 | 0 | Sin nulos |
| `casos_acum` | 0,9 % | 188 | 0 | No se imputan: antes del primer dato el estado aún no publicaba |
| `casos_nuevos` | 0,0 % | 0 | 0 | Sin nulos |
| `muertes_acum` | 4,1 % | 850 | 0 | No se imputan: antes del primer dato el estado aún no publicaba |
| `muertes_nuevas` | 0,0 % | 0 | 0 | Sin nulos |
| `tests_acum` | 0,8 % | 166 | 0 | No se imputan: antes del primer dato el estado aún no publicaba |
| `tests_nuevos` | 0,0 % | 0 | 0 | Sin nulos |
| `fuente_tests` | 0,0 % | 0 | 0 | Sin nulos |
| `hospitalizados_actuales` | 16,6 % | 2.995 | 446 | No se imputan; la cifra nacional de la primavera de 2020 se queda corta |
| `hospitalizados_nuevos` | 0,0 % | 0 | 0 | Sin nulos |
| `uci_actuales` | 44,0 % | 8.437 | 707 | Solo como referencia; no se usa en las conclusiones |
| `ventilador_actuales` | 56,1 % | 10.176 | 1.478 | Solo como referencia; no se usa en las conclusiones |
| `recuperados` | 42,2 % | 8.145 | 632 | Solo como referencia; cada estado la definía a su manera |

- En los acumulados, casi todos los nulos están antes del primer dato: significan «aún no se publicaba», no «cero». Imputar con la media o la mediana no tiene sentido en una cifra que crece cada día, y un 0 falsearía el inicio de la serie.
- Los hospitalizados se empezaron a publicar tarde. Días-estado con dato (50 estados y DC): 9 % en 2020-03, 67 % en 2020-04, 97 % en 2020-07, 100 % en 2021-01. Por eso **la cifra nacional de la primavera de 2020 se queda corta**.

### 1.3 Duplicados

Filas repetidas del mismo estado y día: **0**. No hay nada que eliminar.

## 2. Qué se corrigió

| Problema | Filas | Corrección | Impacto |
| --- | --- | --- | --- |
| Incrementos diarios negativos (correcciones del estado) | 219 | El valor negativo pasa a `NaN` y la fila se marca en `es_correccion` | La suma de incrementos supera al acumulado oficial en un 0,03 % en casos y un 0,20 % en muertes |
| Más positivos acumulados que tests | 59 | Los tests de la fila pasan a `NaN` y se marca en `positivos_sobre_tests` | La positividad por encima del 100 % baja de 17 a 4 valores |
| Positividad de 7 días por encima del 100 % | 4 | Pasa a `NaN` (no es posible) | Son semanas en las que casi no se publicaron tests |

### 2.1 Incrementos negativos

Un estado no puede tener «casos nuevos negativos»: son días en que restó de golpe duplicados o errores de días anteriores. El incremento de cada día es exactamente la diferencia entre dos acumulados seguidos, así que estos días son los días en que el acumulado baja. No se pone un 0 (no sabemos cuántos casos hubo ese día) ni se borra la fila (el resto de sus columnas son válidas). Los acumulados no se tocan: ya incluyen la corrección.

| Columna | Correcciones | Estados | Total restado | La mayor |
| --- | --- | --- | --- | --- |
| `casos_nuevos` | 24 | 14 | -9.584 | -7.757 (MA, 02-09-2020) |
| `muertes_nuevas` | 73 | 25 | -1.043 | -201 (PA, 23-04-2020) |
| `tests_nuevos` | 49 | 23 | -664.505 | -130.545 (KY, 07-11-2020) |
| `hospitalizados_nuevos` | 88 | 25 | -22.063 | -12.257 (CT, 23-10-2020) |

Al quitar las restas, la suma de los incrementos queda algo por encima del último acumulado oficial (50 estados y DC):

| Incremento | Suma de incrementos | Último acumulado | Diferencia |
| --- | --- | --- | --- |
| `casos_nuevos` | 28.652.670 | 28.644.249 | 0,03 % |
| `muertes_nuevas` | 513.972 | 512.929 | 0,20 % |
| `tests_nuevos` | 363.890.935 | 363.228.288 | 0,18 % |

### 2.2 Más positivos que tests

Son 59 filas de 3 estados (WA (38), MI (15), GA (6)), entre el 22-01-2020 y el 24-03-2020: los primeros días de cada serie, cuando los estados publicaban los positivos antes que todos sus tests. La cifra de tests de esas filas está incompleta, así que pasa a `NaN`; los casos se conservan.

## 3. Qué se marcó sin cambiar el valor

Hay datos dudosos que no son errores, o que están en columnas que no se usan en las conclusiones. Se dejan como están y se añade una columna booleana para poder separarlos.

| Marca | Filas | Estados | Detalle | Por qué no se corrige |
| --- | --- | --- | --- | --- |
| `atraso_casos` | 8 | 6 | 0,4 % de `casos_nuevos` | Los casos existieron, solo se publicaron tarde; la media de 7 días los reparte |
| `atraso_muertes` | 58 | 19 | 2,0 % de `muertes_nuevas` | Las muertes existieron, solo se publicaron tarde; la media de 7 días las reparte |
| `atraso_hospitalizados` | 117 | 26 | 11,6 % de `hospitalizados_nuevos` | La columna `hospitalizados_nuevos` no se usa en las conclusiones |
| `ventilador_sobre_uci` | 57 | 9 | PR (33), HI (6), KS (5) | Puede haber respiradores fuera de la UCI; columna no usada |
| `recuperados_sobre_casos` | 69 | 1 | IA (69) | Cada estado definía «recuperado» a su manera; columna no usada |
| `cero_sin_publicar` | 640 | 38 | 55 % en fin de semana | Los casos se publican al día siguiente; la media de 7 días los reparte |

- **Atrasos:** días que multiplican por 5 o más la media de sus vecinos y son atípicos dentro de su estado: un estado que publica de golpe registros de semanas anteriores.
- **Días sin publicar:** días con 0 casos en estados que ya llevaban más de 1.000; 562 son de los 50 estados y DC y el resto de los territorios.
- Reglas de coherencia que no fallan en ninguna fila (2): «Más muertes acumuladas que casos acumulados», «Más pacientes en UCI que hospitalizados».

## 4. Qué quedó pendiente y por qué

- **Tests contados en unidades distintas.** Al cierre, los estados usaban 4 unidades distintas (`totalTestsViral` en 29, `totalTestEncountersViral` en 14, `posNeg` en 11, `totalTestsPeopleViral` en 2). No se pueden convertir unas en otras con estos datos: la positividad sirve para ver la tendencia de un estado, pero las comparaciones entre estados son aproximadas.
- **Hospitalizados incompletos al principio.** `hospitalizados_actuales` tiene un 16,6 % de nulos, sobre todo en la primavera de 2020. No se pueden reconstruir los días en que un estado aún no lo publicaba; al interpretar esa época hay que tener en cuenta que la cifra nacional se queda corta.
- **UCI, respirador y recuperados.** Entre un 42 % y un 56 % de nulos y definiciones distintas en cada estado: se conservan como referencia, sin sacar conclusiones de ellas.
- **Atrasos que duran varios días.** El criterio solo detecta los volcados más claros: Ohio sumó 721 el 11-02-2021, 2.559 el 12-02-2021 (marcado), 1.204 el 13-02-2021. Los días de alrededor no salen marcados porque su media de vecinos ya incluye el pico. Por eso las series temporales usan la media de 7 días, que amortigua también los que se escapan.
- **Totales a partir de incrementos.** Por las correcciones quitadas, la suma de los incrementos queda algo por encima del acumulado oficial (apartado 2.1). Para la cifra oficial exacta de un estado hay que usar su último acumulado.
- **Territorios sin población.** AS, GU, MP, VI no están en la tabla del US Census Bureau: sus 1.428 filas no tienen tasas por 100.000 habitantes. Las comparaciones por habitante se hacen con los 50 estados, DC y Puerto Rico.
- **Casos sin detectar en la primera ola.** En la primavera de 2020 se hacían muy pocos tests y solo se detectaban los casos graves. Con estos datos no se puede estimar cuántos casos reales hubo, así que las comparaciones de casos entre olas se interpretan con cuidado (las muertes son más comparables).
