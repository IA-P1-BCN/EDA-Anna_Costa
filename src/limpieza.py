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


COLUMNAS_ATRASO = {
    "casos_nuevos": "atraso_casos",
    "muertes_nuevas": "atraso_muertes",
    "hospitalizados_nuevos": "atraso_hospitalizados",
}


def limites_iqr(serie: pd.Series, k: float = 1.5) -> tuple[float, float]:
    """Límites inferior y superior de la regla del rango intercuartílico: Q1 - k·IQR y Q3 + k·IQR."""
    q1, q3 = serie.quantile([0.25, 0.75])
    return q1 - k * (q3 - q1), q3 + k * (q3 - q1)


def media_vecinos(serie: pd.Series, ventana: int = 15) -> pd.Series:
    """Media de los días de alrededor (ventana centrada) sin contar el propio día."""
    suma = serie.rolling(ventana, center=True, min_periods=ventana // 2).sum()
    cuenta = serie.rolling(ventana, center=True, min_periods=ventana // 2).count()
    return (suma - serie.fillna(0)) / (cuenta - serie.notna())


def marcar_atrasos(
    df: pd.DataFrame,
    columnas: dict = COLUMNAS_ATRASO,
    factor: float = 5,
    minimo: float = 20,
    ventana: int = 15,
) -> pd.DataFrame:
    """Marca los días que parecen atrasos de notificación y no sucesos de ese día.

    Un día es atraso si cumple las tres condiciones dentro de su estado:
    - es atípico por la regla del IQR calculada con los datos de ese estado,
    - multiplica por `factor` o más la media de los días vecinos (es un pico aislado),
    - supera `minimo`, para no marcar saltos de 1 a 6 en estados muy pequeños.

    El valor no se toca: solo se añade una columna booleana por variable.
    """
    df = df.sort_values(["estado", "fecha"]).copy()
    for columna, marca in columnas.items():
        por_estado = df.groupby("estado")[columna]
        limite = por_estado.transform(lambda s: limites_iqr(s)[1])
        vecinos = por_estado.transform(lambda s: media_vecinos(s, ventana))
        df[marca] = (df[columna] > limite) & (df[columna] >= factor * vecinos) & (df[columna] >= minimo)
    return df


def limpiar(df_crudo: pd.DataFrame) -> pd.DataFrame:
    """Aplica toda la limpieza en orden y deja los datos ordenados por estado y fecha."""
    df = convertir_fecha(df_crudo)
    df = seleccionar_y_renombrar(df)
    df = marcar_correcciones(df)
    df = marcar_territorios(df)
    df = marcar_atrasos(df)
    return df.sort_values(["estado", "fecha"]).reset_index(drop=True)
