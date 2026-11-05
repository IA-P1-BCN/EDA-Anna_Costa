# COVID-19 en Estados Unidos: análisis exploratorio de datos

Análisis exploratorio (EDA) de los datos diarios de COVID-19 por estado en Estados Unidos, de enero de 2020
a marzo de 2021: carga, limpieza, exploración y conclusiones para un público no técnico.

El enunciado del proyecto está en [docs/ENUNCIADO.md](docs/ENUNCIADO.md).

**Informe ejecutivo** (2 páginas, para público no técnico):
[reports/informe_ejecutivo.pdf](reports/informe_ejecutivo.pdf).

**Gráficos interactivos** (regiones y olas, se abren en el navegador): [reports/interactivos/](reports/interactivos/).

## Datos

- **Fuente:** [The COVID Tracking Project](https://covidtracking.com/data/download) (The Atlantic), licencia
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Descarga:** `https://api.covidtracking.com/v1/states/daily.csv`
- **Contenido:** 20.780 filas y 56 columnas, con una fila por estado o territorio y por día (50 estados,
  Washington D. C. y 5 territorios), del 13-01-2020 al 07-03-2021. Recoge casos, tests, hospitalizaciones
  y fallecimientos, tanto acumulados como diarios.

**Segunda fuente, población por estado** (notebook 05):

- **Fuente:** [US Census Bureau, Population Estimates Program](https://www.census.gov/programs-surveys/popest.html),
  *Annual Estimates of the Resident Population for the United States, Regions, States, District of Columbia, and
  Puerto Rico* (serie 2020-2023, Vintage 2023). Datos públicos del Gobierno de Estados Unidos.
- **Descarga:** `https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/state/totals/NST-EST2023-ALLDATA.csv`
- **Uso:** población a 1 de julio de 2020 (`POPESTIMATE2020`), unida a los datos de COVID por código FIPS para
  calcular tasas por cada 100.000 habitantes.

No hace falta descargar nada a mano: la primera vez que se ejecuta, el notebook baja el CSV a `data/raw/` y
guarda la versión limpia en `data/processed/`. Las dos carpetas están en `.gitignore`.

## Estructura

```text
├── notebooks/
│   ├── 01_eda_covid.ipynb   # carga, limpieza y análisis básico
│   ├── 02_outliers.ipynb    # valores atípicos y justificación de la limpieza
│   ├── 03_variables_y_agrupaciones.ipynb  # variables nuevas, groupby y pivot_table
│   ├── 04_correlaciones_y_tendencias.ipynb # correlaciones, desfases y tendencias
│   ├── 05_normalizar_poblacion.ipynb       # población del Census Bureau y tasas por 100.000 habitantes
│   ├── 06_calidad_y_transformaciones.ipynb # datos dudosos, media móvil y escala logarítmica
│   └── 07_segmentos_plotly.ipynb           # regiones y olas con gráficos interactivos
├── src/
│   ├── limpieza.py          # funciones de carga y limpieza
│   ├── variables.py         # variables derivadas (ola, región, positividad, letalidad)
│   ├── poblacion.py         # carga de la población y unión por código FIPS
│   ├── calidad.py           # reglas de coherencia, correcciones y días sin publicar
│   ├── transformaciones.py  # media móvil, efecto del día de la semana y logaritmo
│   ├── graficos.py          # estilo común de los gráficos
│   ├── interactivos.py      # colores por región y estilo de los gráficos de plotly
│   └── informe.py           # genera el informe ejecutivo en PDF
├── reports/
│   ├── informe_ejecutivo.pdf
│   ├── figuras/             # gráficos del informe
│   └── interactivos/        # gráficos de plotly en HTML
├── data/                    # se crea al ejecutar (no se sube al repositorio)
│   ├── raw/
│   └── processed/
├── docs/
│   └── ENUNCIADO.md
└── requirements.txt
```

## Instalación

Hace falta Python 3.12 o superior.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Ejecución

Desde la raíz del repositorio y con el entorno activado:

```bash
jupyter notebook notebooks/01_eda_covid.ipynb
```

Después: *Kernel → Restart & Run All*. También puede abrirse en VS Code seleccionando el intérprete de `.venv`.

Los notebooks se ejecutan **en orden** (01, 02, 03, 04, 05, 06, 07...): cada uno guarda en `data/processed/` los datos que usa el
siguiente.

Para ejecutarlos enteros sin abrirlos:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda_covid.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_outliers.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/03_variables_y_agrupaciones.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/04_correlaciones_y_tendencias.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/05_normalizar_poblacion.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/06_calidad_y_transformaciones.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/07_segmentos_plotly.ipynb
```

El informe ejecutivo se genera después de los notebooks 01 a 03 (todas sus cifras se calculan a partir de los datos):

```bash
python -m src.informe
```

## Qué hay en el análisis

1. **Revisión de la estructura:** `shape`, `info()`, `head()` y `describe()`.
2. **Limpieza:**
   - Valores faltantes y duplicados.
   - Conversión de la fecha.
   - Se descartan 41 columnas, con el motivo de cada una.
   - Renombrado al castellano.
   - Tratamiento de los incrementos diarios negativos (correcciones de los estados).
3. **Análisis univariado:** casos diarios, muertes diarias y unidad de medida de los tests.
4. **Análisis bivariado:** evolución en el tiempo, ranking de estados, hospitalizados frente a muertes y
   retraso entre casos y muertes.
5. **Valores atípicos** (notebook 02):
   - Por qué el IQR global no sirve con estados de tamaños tan distintos.
   - IQR por estado: la mayoría de los atípicos son los picos de la ola de invierno.
   - Detección de atrasos de notificación (picos aislados) y qué hacer con cada tipo.
   - Repaso de todas las decisiones de limpieza con sus alternativas.
6. **Variables nuevas y agrupaciones** (notebook 03):
   - Año, mes y semana; ola (cortada en los valles de la curva); región del Census Bureau.
   - Tasa de positividad de 7 días y letalidad aparente.
   - Resúmenes por ola, región y estado con `groupby` y `agg`, y `pivot_table` de positividad por región y mes.
7. **Correlaciones y tendencias** (notebook 04):
   - Matriz de correlación calculada dentro de cada estado (y por qué no mezclando todas las filas) con mapa de calor.
   - Desfases entre casos, hospitalizados y muertes.
   - Tendencias nacionales, orden de las variables en la ola de invierno, positividad por región y cuatro estados.
8. **Normalizar por población** (notebook 05):
   - Población por estado del US Census Bureau, unida con `merge` por código FIPS y comprobación de que no se
     pierden filas ni estados.
   - Casos, muertes y máximo de hospitalizados por cada 100.000 habitantes.
   - Ranking de estados absoluto frente a ranking por habitante, y muertes por habitante de cada región en cada ola.
9. **Calidad de los datos y transformaciones** (notebook 06):
   - Reglas de coherencia entre columnas (positivos y tests, muertes y casos, UCI, respirador y recuperados).
   - Incrementos diarios frente a acumulados y correcciones por estado y fecha.
   - Días sin publicar (ceros que no son ceros) y efecto del día de la semana.
   - Media móvil de 7 días y escala logarítmica, con su justificación, y tabla con el tratamiento de cada tipo de
     dato dudoso.
10. **Regiones y olas con `plotly`** (notebook 07):
    - Mapa de las cuatro regiones del Census Bureau.
    - Casos, hospitalizados y muertes por habitante de cada región en el tiempo, con botones para cambiar de
      variable y zoom.
    - Mapa de muertes por habitante de cada estado con un botón por ola.
    - Estados de cada región por ola (cajas con un punto por estado) y tabla resumen con tests, positividad y
      letalidad aparente.

## Conclusiones principales

- **Tres olas:** primavera de 2020, verano de 2020 e invierno de 2020-2021. La peor fue la de enero de 2021,
  con unos 247.000 casos y 3.300 muertes al día (media de 7 días).
- **Concentración por estados:** California, Texas, Florida, Nueva York e Illinois suman el 38 % de los casos.
  Son cifras absolutas, que reflejan sobre todo la población de cada estado.
- **Anticipo de las muertes:** los hospitalizados y las muertes diarias van muy de la mano (r = 0,87), y los
  casos anticipan las muertes en unos 23 días.
- **Atípicos:** casi 9 de cada 10 días atípicos de un estado caen en la ola de invierno y son reales. Los
  problemáticos son los atrasos de notificación (por ejemplo, 2.559 muertes en Ohio el 12-02-2021): se mantienen
  y se marcan. Los hospitalizados nuevos acumulan tantos saltos que no se usan.
- **Cada ola tuvo su zona:** el Noreste concentró el 53 % de las muertes de la primavera de 2020, el Sur el 55 % de
  los casos del verano, y la ola de otoño-invierno se repartió por todo el país casi en proporción a la población.
- **Letalidad aparente:** bajó del 5,8 % (mayo de 2020) a menos del 2 %, sobre todo porque al principio se hacían
  pocos tests y solo se detectaban los casos graves.
- **Cadena casos → hospitalizados → muertes:** dentro de cada estado, los hospitalizados siguen a los casos en unos
  3 días y las muertes a los hospitalizados en unos 11. Los hospitalizados son el mejor aviso de las muertes.
- **Por habitante, el ranking cambia:** el de muertes absolutas sigue casi al de población (Spearman 0,94).
  Por cada 100.000 habitantes, California, Texas y Florida bajan a mitad de tabla y Nueva Jersey es el estado con
  más muertes (254), seguido de Massachusetts y Rhode Island. En la primavera de 2020 el Noreste tuvo unas 100
  muertes por cada 100.000 habitantes, una cifra comparable a la de cada región en toda la ola de otoño-invierno
  (entre 89 y 112).
- **Calidad de los datos:** los datos imposibles son pocos y están localizados (59 filas con más positivos que
  tests, todas en marzo de 2020 o antes). Lo que más distorsiona es el calendario de publicación: 562 días con 0
  casos en estados con miles de casos y muertes del lunes al 55 % de lo normal. Por eso las series se ven con
  media de 7 días.
- **Regiones:** el Medio Oeste fue el primero en la ola de otoño-invierno (pico de casos el 19-11-2020, casi dos
  meses antes que el resto). Dentro de cada región hay mucha variedad: en la primavera de 2020, Nueva Jersey
  tuvo 151 muertes por 100.000 habitantes y Maine, 7. En invierno, el Noreste hizo el doble de tests por
  habitante que el Sur, con la mitad de positividad.

## Limitaciones

- La población es la de 1 de julio de 2020 para todo el periodo, y no hay datos por edad: no se puede saber si un
  estado tuvo más muertes por habitante porque su población es más mayor.
- En la primavera de 2020 se hacían pocos tests, así que los casos de la primera ola están infracontados.
- Cada estado medía los tests y las hospitalizaciones a su manera: unos cuentan personas y otros muestras, así que
  la positividad no se puede comparar entre estados con distinta forma de contar.
