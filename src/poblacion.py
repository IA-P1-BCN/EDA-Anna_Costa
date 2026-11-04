"""Población por estado (US Census Bureau) y tasas por cada 100.000 habitantes."""

from pathlib import Path

import pandas as pd
import requests

# Estimaciones de población del US Census Bureau, serie 2020-2023 (Vintage 2023), por estado.
URL_POBLACION = (
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/state/totals/NST-EST2023-ALLDATA.csv"
)

# Población a 1 de julio de 2020: el punto medio del periodo de los datos (marzo 2020 - marzo 2021).
COLUMNA_POBLACION = "POPESTIMATE2020"

# SUMLEV 40 = estado (incluye DC y Puerto Rico). Las filas 10, 20 y 30 son país, regiones y divisiones.
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
    poblacion = estados.rename(columns={"STATE": "fips", "NAME": "nombre_estado", columna: "poblacion"})
    poblacion = poblacion[["fips", "nombre_estado", "poblacion"]].astype({"fips": int, "poblacion": int})
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
