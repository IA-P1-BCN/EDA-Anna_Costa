"""Datos pequeños de ejemplo para los tests: tres días de dos estados y un territorio."""

import numpy as np
import pandas as pd
import pytest

from src import limpieza, poblacion
from src.limpieza import COLUMNAS
from src.pipeline import ORIGINALES

# Imita el CSV del US Census Bureau: el país (SUMLEV 10) y dos estados (SUMLEV 40). Guam no está.
CENSO_CSV = (
    "SUMLEV,STATE,NAME,POPESTIMATE2020\n"
    "10,0,United States,331000000\n"
    "40,36,New York,20000000\n"
    "40,50,Vermont,600000\n"
)


@pytest.fixture(name="crudo")
def fixture_crudo():
    """Imita el CSV de The COVID Tracking Project: columnas en inglés y fecha como entero."""
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


@pytest.fixture(name="renombrado")
def fixture_renombrado(crudo):
    """El mismo ejemplo con las columnas ya en castellano y la fecha convertida."""
    df = crudo[list(COLUMNAS)].rename(columns=COLUMNAS)
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str), format="%Y%m%d")
    return df


@pytest.fixture(name="serie_estado")
def fixture_serie_estado():
    """Fábrica: un estado con el mismo valor diario en casos, muertes y hospitalizados nuevos."""
    def hacer(estado: str, valores: list, desde: str = "2020-10-01") -> pd.DataFrame:
        fechas = pd.date_range(desde, periods=len(valores), freq="D")
        return pd.DataFrame({
            "estado": estado, "fecha": fechas,
            "casos_nuevos": valores, "muertes_nuevas": valores, "hospitalizados_nuevos": valores,
        })
    return hacer


@pytest.fixture(name="carpeta_raw")
def fixture_carpeta_raw(tmp_path, crudo, monkeypatch):
    """data/raw/ con los dos originales ya descargados; si algo intenta descargar, el test falla."""
    raw = tmp_path / "raw"
    raw.mkdir()
    crudo.to_csv(raw / ORIGINALES["covid"], index=False)
    (raw / ORIGINALES["censo"]).write_bytes(CENSO_CSV.encode("latin-1"))

    def no_descargar(*_args, **_kwargs):
        pytest.fail("no debería descargar")

    monkeypatch.setattr(limpieza.requests, "get", no_descargar)
    monkeypatch.setattr(poblacion.requests, "get", no_descargar)
    return raw
