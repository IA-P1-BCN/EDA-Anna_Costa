"""Pipeline de datos: descarga, limpia y guarda en data/processed/ todo lo que leen los notebooks.

Uso, desde la raíz del repositorio y con el entorno activado:

    python -m src.pipeline               # usa los originales de data/raw/ si ya están descargados
    python -m src.pipeline --descargar   # vuelve a descargar los originales

Pasos (los mismos que hacen los notebooks, con las funciones de src/):

1. Carga los datos de The COVID Tracking Project, los limpia y comprueba que son válidos.
2. Crea las variables nuevas: año, mes, semana, ola, región, positividad y letalidad.
3. Añade la población del US Census Bureau y las tasas por cada 100.000 habitantes.
4. Marca los datos dudosos y vacía los tests imposibles.

Cada paso guarda su resultado en data/processed/. Si los datos limpios no pasan la validación,
el pipeline se para sin escribir ningún fichero.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.calidad import tratar_calidad
from src.limpieza import cargar_datos, limpiar, validar_limpios
from src.poblacion import cargar_poblacion, preparar_poblacion, tasas_100k_7d, unir_poblacion
from src.variables import crear_variables, positividad_7d

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_RAW = RAIZ / "data" / "raw"
CARPETA_PROCESSED = RAIZ / "data" / "processed"

ORIGINALES = {
    "covid": "covid_states_daily.csv",
    "censo": "poblacion_estados_census.csv",
}

# Ficheros que genera, en orden. Cada uno es la entrada de un notebook.
SALIDAS = {
    "limpio": "covid_estados_limpio.csv",          # notebook 03
    "variables": "covid_estados_variables.csv",    # notebooks 04 y 05
    "poblacion": "covid_estados_poblacion.csv",    # notebook 06
    "final": "covid_estados_final.csv",            # notebook 07
}

log = logging.getLogger(__name__)


def preparar_datos(crudo: pd.DataFrame, censo: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Aplica los cuatro pasos y devuelve la tabla de cada uno, sin escribir nada."""
    limpio = validar_limpios(limpiar(crudo))
    variables = crear_variables(limpio)
    con_poblacion = tasas_100k_7d(unir_poblacion(variables, preparar_poblacion(censo)))
    final = tratar_calidad(con_poblacion)
    final["positividad_7d"] = positividad_7d(final)   # con los tests imposibles ya vacíos
    return {"limpio": limpio, "variables": variables, "poblacion": con_poblacion, "final": final}


def ejecutar(raw: Path = CARPETA_RAW, processed: Path = CARPETA_PROCESSED,
             descargar: bool = False) -> dict[str, Path]:
    """Ejecuta el pipeline completo y devuelve la ruta de cada fichero generado."""
    raw, processed = Path(raw), Path(processed)
    ruta_covid = raw / ORIGINALES["covid"]
    ruta_censo = raw / ORIGINALES["censo"]
    if descargar:
        # cargar_datos() y cargar_poblacion() descargan el fichero cuando no lo encuentran.
        ruta_covid.unlink(missing_ok=True)
        ruta_censo.unlink(missing_ok=True)

    log.info("Cargando los originales de %s", raw)
    crudo = cargar_datos(ruta_covid)
    censo = cargar_poblacion(ruta_censo)
    log.info("  COVID: %s filas | censo: %s filas", f"{len(crudo):,}".replace(",", "."), len(censo))

    tablas = preparar_datos(crudo, censo)

    processed.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for nombre, tabla in tablas.items():
        ruta = processed / SALIDAS[nombre]
        tabla.to_csv(ruta, index=False)
        rutas[nombre] = ruta
        filas = f"{len(tabla):,}".replace(",", ".")
        log.info("  Guardado %s (%s filas x %s columnas)", ruta.name, filas, tabla.shape[1])
    return rutas


def main(argumentos: list[str] | None = None) -> None:
    """Punto de entrada de `python -m src.pipeline`."""
    lector = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    lector.add_argument("--descargar", action="store_true",
                        help="vuelve a descargar los datos originales aunque ya estén en data/raw/")
    opciones = lector.parse_args(argumentos)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ejecutar(descargar=opciones.descargar)
    log.info("Listo: los notebooks ya pueden leer los datos de %s", CARPETA_PROCESSED)


if __name__ == "__main__":
    main()
