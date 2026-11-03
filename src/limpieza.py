"""Funciones de carga y limpieza del dataset COVID Tracking Project (por estado y día)."""

from pathlib import Path

import numpy as np
import pandas as pd
import requests

URL_DATOS = "https://api.covidtracking.com/v1/states/daily.csv"

# Columnas que se conservan y su nombre en castellano.
COLUMNAS = {
    "date": "fecha",
    "state": "estado",
    "fips": "fips",
    "positive": "casos_acum",
    "positiveIncrease": "casos_nuevos",
    "death": "muertes_acum",
    "deathIncrease": "muertes_nuevas",
    "totalTestResults": "tests_acum",
    "totalTestResultsIncrease": "tests_nuevos",
    "totalTestResultsSource": "fuente_tests",
    "hospitalizedCurrently": "hospitalizados_actuales",
    "hospitalizedIncrease": "hospitalizados_nuevos",
    "inIcuCurrently": "uci_actuales",
    "onVentilatorCurrently": "ventilador_actuales",
    "recovered": "recuperados",
}

COLUMNAS_INCREMENTO = ["casos_nuevos", "muertes_nuevas", "tests_nuevos", "hospitalizados_nuevos"]

# Territorios no estatales (DC se trata como estado: tiene votos electorales y datos completos).
TERRITORIOS = {"AS", "GU", "MP", "PR", "VI"}


def cargar_datos(ruta: Path, url: str = URL_DATOS) -> pd.DataFrame:
    """Lee el CSV local; si no existe, lo descarga una vez y lo guarda."""
    ruta = Path(ruta)
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        respuesta = requests.get(url, timeout=120)
        respuesta.raise_for_status()
        ruta.write_bytes(respuesta.content)
    return pd.read_csv(ruta)


def convertir_fecha(df: pd.DataFrame, columna: str = "date") -> pd.DataFrame:
    """Convierte un entero tipo 20200313 en fecha."""
    df = df.copy()
    df[columna] = pd.to_datetime(df[columna].astype(str), format="%Y%m%d")
    return df


def seleccionar_y_renombrar(df: pd.DataFrame, columnas: dict = COLUMNAS) -> pd.DataFrame:
    """Se queda con las columnas útiles y les pone nombre en castellano."""
    return df[list(columnas)].rename(columns=columnas)


def marcar_correcciones(df: pd.DataFrame, columnas: list = COLUMNAS_INCREMENTO) -> pd.DataFrame:
    """Los incrementos diarios negativos son correcciones del estado, no sucesos reales.

    Se marca la fila en `es_correccion` y el valor negativo pasa a NaN, para que no
    distorsione distribuciones ni medias. Las columnas acumuladas no se tocan.
    """
    df = df.copy()
    negativos = df[columnas] < 0
    df["es_correccion"] = negativos.any(axis=1)
    df[columnas] = df[columnas].mask(negativos, np.nan)
    return df


def marcar_territorios(df: pd.DataFrame, territorios: set = TERRITORIOS) -> pd.DataFrame:
    """Añade `es_territorio` para poder separar los 50 estados + DC de los territorios."""
    df = df.copy()
    df["es_territorio"] = df["estado"].isin(territorios)
    return df


def limpiar(df_crudo: pd.DataFrame) -> pd.DataFrame:
    """Aplica toda la limpieza en orden y deja los datos ordenados por estado y fecha."""
    df = convertir_fecha(df_crudo)
    df = seleccionar_y_renombrar(df)
    df = marcar_correcciones(df)
    df = marcar_territorios(df)
    return df.sort_values(["estado", "fecha"]).reset_index(drop=True)
