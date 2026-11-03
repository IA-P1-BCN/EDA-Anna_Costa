# COVID-19 en Estados Unidos: análisis exploratorio de datos

Análisis exploratorio (EDA) de los datos diarios de COVID-19 por estado en Estados Unidos, de enero de 2020
a marzo de 2021: carga, limpieza, exploración y conclusiones para un público no técnico.

El enunciado del proyecto está en [docs/ENUNCIADO.md](docs/ENUNCIADO.md).

## Datos

- **Fuente:** [The COVID Tracking Project](https://covidtracking.com/data/download) (The Atlantic), licencia
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Descarga:** `https://api.covidtracking.com/v1/states/daily.csv`
- **Contenido:** 20.780 filas y 56 columnas, con una fila por estado o territorio y por día (50 estados,
  Washington D. C. y 5 territorios), del 13-01-2020 al 07-03-2021. Recoge casos, tests, hospitalizaciones
  y fallecimientos, tanto acumulados como diarios.

No hace falta descargar nada a mano: la primera vez que se ejecuta, el notebook baja el CSV a `data/raw/` y
guarda la versión limpia en `data/processed/`. Las dos carpetas están en `.gitignore`.

## Estructura

```text
├── notebooks/
│   ├── 01_eda_covid.ipynb   # carga, limpieza y análisis básico
│   └── 02_outliers.ipynb    # valores atípicos y justificación de la limpieza
├── src/
│   ├── limpieza.py          # funciones de carga y limpieza
│   └── graficos.py          # estilo común de los gráficos
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

Los notebooks se ejecutan **en orden** (01, 02...): cada uno guarda en `data/processed/` los datos que usa el
siguiente.

Para ejecutarlos enteros sin abrirlos:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda_covid.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_outliers.ipynb
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

## Limitaciones

- Las cifras aún no están normalizadas por población.
- En la primavera de 2020 se hacían pocos tests, así que los casos de la primera ola están infracontados.
- Cada estado medía los tests y las hospitalizaciones a su manera.
