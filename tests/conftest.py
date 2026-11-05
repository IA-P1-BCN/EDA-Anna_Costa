"""Datos pequeños de ejemplo para los tests: tres días de dos estados y un territorio."""

import numpy as np
import pandas as pd
import pytest

from src.limpieza import COLUMNAS


@pytest.fixture
def crudo():
    """Imita el CSV original de The COVID Tracking Project (nombres en inglés, fecha como entero)."""
    return pd.DataFrame({
        "date": [20200301, 20200302, 20200303] * 3,
        "state": ["NY"] * 3 + ["VT"] * 3 + ["GU"] * 3,
        "fips": [36] * 3 + [50] * 3 + [66] * 3,
        "positive": [10, 15, 14, 1, 2, 3, 0, 0, 1],
        "positiveIncrease": [10, 5, -1, 1, 1, 1, 0, 0, 1],
        "death": [0, 1, 2, 0, 0, 0, 0, 0, 0],
        "deathIncrease": [0, 1, 1, 0, 0, 0, 0, 0, 0],
        "totalTestResults": [100, 150, 200, 10, 20, 30, 5, 6, 7],
        "totalTestResultsIncrease": [100, 50, 50, 10, 10, 10, 5, 1, 1],
        "totalTestResultsSource": ["totalTestsViral"] * 9,
        "hospitalizedCurrently": [5, 6, 7, np.nan, 1, 1, np.nan, np.nan, np.nan],
        "hospitalizedIncrease": [5, 1, 1, 0, 1, 0, 0, 0, 0],
        "inIcuCurrently": [1, 2, 2, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        "onVentilatorCurrently": [0, 1, 3, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        "recovered": [np.nan] * 9,
        "dataQualityGrade": ["A"] * 9,   # columna que la limpieza descarta
    })


@pytest.fixture
def renombrado(crudo):
    """El mismo ejemplo con las columnas ya en castellano y la fecha convertida."""
    df = crudo[list(COLUMNAS)].rename(columns=COLUMNAS)
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str), format="%Y%m%d")
    return df


@pytest.fixture
def serie_estado():
    """Fábrica: un estado con el mismo valor diario en casos, muertes y hospitalizados nuevos."""
    def hacer(estado: str, valores: list, desde: str = "2020-10-01") -> pd.DataFrame:
        fechas = pd.date_range(desde, periods=len(valores), freq="D")
        return pd.DataFrame({
            "estado": estado, "fecha": fechas,
            "casos_nuevos": valores, "muertes_nuevas": valores, "hospitalizados_nuevos": valores,
        })
    return hacer
