"""Población por estado (US Census Bureau) y tasas por cada 100.000 habitantes."""

from pathlib import Path

import pandas as pd
import requests

# Estimaciones de población del US Census Bureau, serie 2020-2023 (Vintage 2023), por estado.
URL_POBLACION = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2020-2023/state/totals/NST-EST2023-ALLDATA.csv"
)

# Población a 1 de julio de 2020: el punto medio del periodo de los datos (marzo 2020 - marzo 2021).
COLUMNA_POBLACION = "POPESTIMATE2020"

# SUMLEV 40 = estado (incluye DC y Puerto Rico).
# Las filas 10, 20 y 30 son país, regiones y divisiones.
NIVEL_ESTADO = 40

POR_HABITANTES = 100_000


def cargar_poblacion(ruta: Path, url: str = URL_POBLACION) -> pd.DataFrame:
    """Lee el CSV del Census Bureau; si no existe, lo descarga una vez y lo guarda."""
    ruta = Path(ruta)
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        respuesta = requests.get(url, timeout=120)
        respuesta.raise_for_status()
        ruta.write_bytes(respuesta.content)
    # El fichero del Census Bureau no está en UTF-8.
    return pd.read_csv(ruta, encoding="latin-1")


def preparar_poblacion(censo: pd.DataFrame, columna: str = COLUMNA_POBLACION) -> pd.DataFrame:
    """Una fila por estado: código FIPS, nombre y población."""
    estados = censo[censo["SUMLEV"] == NIVEL_ESTADO]
    nombres = {"STATE": "fips", "NAME": "nombre_estado", columna: "poblacion"}
    poblacion = estados.rename(columns=nombres)[list(nombres.values())]
    poblacion = poblacion.astype({"fips": int, "poblacion": int})
    if poblacion["fips"].duplicated().any():
        raise ValueError("Hay códigos FIPS repetidos en la tabla de población")
    return poblacion.reset_index(drop=True)


def unir_poblacion(df: pd.DataFrame, poblacion: pd.DataFrame) -> pd.DataFrame:
    """Añade la población de cada estado por su código FIPS sin perder ni duplicar filas."""
    unido = df.merge(poblacion, on="fips", how="left", validate="many_to_one")
    if len(unido) != len(df):
        raise ValueError(f"El merge cambia el número de filas: {len(df)} -> {len(unido)}")
    return unido


def por_100k(valor, poblacion):
    """Cifra por cada 100.000 habitantes (sirve con números, Series o columnas)."""
    return valor / poblacion * POR_HABITANTES


# Columnas diarias que se pasan a media de 7 días por cada 100.000 habitantes.
TASAS_100K_7D = {
    "casos_nuevos": "casos_100k_7d",
    "muertes_nuevas": "muertes_100k_7d",
    "hospitalizados_actuales": "hospitalizados_100k_7d",
}


def tasas_100k_7d(df: pd.DataFrame, columnas: dict | None = None) -> pd.DataFrame:
    """Añade la media de 7 días de cada columna por cada 100.000 habitantes, dentro de cada estado.

    Basta con 4 días con dato en la semana, así una corrección (NaN) no deja la semana vacía.
    Necesita la columna `poblacion` (ver unir_poblacion); sin población, la tasa queda en NaN.
    `columnas` es {columna diaria: columna de la tasa}; por defecto, TASAS_100K_7D.
    """
    df = df.sort_values(["estado", "fecha"]).copy()
    for origen, destino in (columnas or TASAS_100K_7D).items():
        media_7d = df.groupby("estado")[origen].transform(
            lambda s: s.rolling(7, min_periods=4).mean())
        df[destino] = por_100k(media_7d, df["poblacion"])
    return df
