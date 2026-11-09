"""Tests de src/calidad.py."""

import numpy as np
import pandas as pd
import pytest

from src.calidad import (
    comprobar_incrementos,
    diferencia_totales,
    marcar_ceros_sin_publicar,
    resumir_correcciones,
    resumir_marcas,
    revisar_coherencia,
    tratar_calidad,
)


@pytest.fixture(name="datos")
def fixture_datos():
    """Dos estados, tres días, con una incoherencia de cada tipo en NY."""
    return pd.DataFrame({
        "estado": ["NY"] * 3 + ["VT"] * 3,
        "fecha": pd.to_datetime(["2020-03-01", "2020-03-02", "2020-03-03"] * 2),
        "casos_acum": [50, 1500, 1500, 1, 2, 3],
        "casos_nuevos": [50, 1450, 0, 1, 1, 1],
        "muertes_acum": [0, 10, 12, 0, 0, 0],
        "muertes_nuevas": [0, 10, 2, 0, 0, 0],
        "tests_acum": [20, 3000, 3100, 10, 20, 30],      # NY 01-03: más positivos que tests
        "tests_nuevos": [20, 2980, 100, 10, 10, 10],
        "hospitalizados_actuales": [5, 50, 60, np.nan, 1, 1],
        "uci_actuales": [1, 10, 8, np.nan, np.nan, np.nan],
        # NY 02-03: más respirador que UCI
        "ventilador_actuales": [0, 12, 4, np.nan, np.nan, np.nan],
        # NY 02-03: 1495 recuperados + 10 muertes > 1500 casos
        "recuperados": [np.nan, 1495, np.nan, np.nan, np.nan, np.nan],
    })


def test_revisar_coherencia_marca_cada_regla(datos):
    """Cada fila imposible se marca en la regla que incumple, y solo en esa."""
    marcas = revisar_coherencia(datos)

    assert marcas["positivos_sobre_tests"].tolist() == [True, False, False, False, False, False]
    assert marcas["ventilador_sobre_uci"].tolist() == [False, True, False, False, False, False]
    assert marcas["recuperados_sobre_casos"].tolist() == [False, True, False, False, False, False]
    assert not marcas["muertes_sobre_casos"].any()
    assert not marcas["uci_sobre_hospitalizados"].any()


def test_revisar_coherencia_no_marca_las_filas_sin_dato(datos):
    """Un dato que falta (NaN) no incumple ninguna regla."""
    marcas = revisar_coherencia(datos)

    # VT no tiene UCI ni respirador.
    assert not marcas.loc[datos["estado"] == "VT"].any().any()


def test_resumir_marcas(datos):
    """El resumen cuenta las filas de cada regla y nombra los estados con más."""
    resumen = resumir_marcas(datos, revisar_coherencia(datos))

    assert resumen.loc["positivos_sobre_tests", "filas"] == 1
    assert resumen.loc["positivos_sobre_tests", "principales"] == "NY (1)"
    assert resumen.loc["muertes_sobre_casos", "filas"] == 0


def test_comprobar_incrementos_coherentes(datos):
    """Si los incrementos cuadran con los acumulados, no hay diferencias."""
    tabla = comprobar_incrementos(datos)

    assert (tabla["no_coinciden"] == 0).all()
    # El primer día de cada estado no tiene día anterior con el que comparar.
    assert tabla.loc["casos_nuevos", "filas_comparadas"] == 4


def test_comprobar_incrementos_detecta_un_incremento_que_no_cuadra(datos):
    """Un incremento distinto de la diferencia de acumulados se cuenta."""
    datos.loc[1, "casos_nuevos"] = 999
    tabla = comprobar_incrementos(datos)

    assert tabla.loc["casos_nuevos", "no_coinciden"] == 1


def test_comprobar_incrementos_cuenta_los_acumulados_que_bajan(datos):
    """Un acumulado que baja se cuenta aparte, no como incremento erróneo."""
    datos.loc[2, "muertes_acum"] = 8
    datos.loc[2, "muertes_nuevas"] = -2
    tabla = comprobar_incrementos(datos)

    assert tabla.loc["muertes_nuevas", "acumulado_baja"] == 1
    assert tabla.loc["muertes_nuevas", "no_coinciden"] == 0


def test_resumir_correcciones():
    """Cuenta las correcciones, cuánto restan y qué estado resta más."""
    crudo = pd.DataFrame({
        "estado": ["MA", "MA", "PA"],
        "fecha": pd.to_datetime(["2020-09-01", "2020-09-02", "2020-04-23"]),
        "casos_nuevos": [100, -7757, -5],
    })
    tabla = resumir_correcciones(crudo, ["casos_nuevos"])

    assert tabla.loc["casos_nuevos", "correcciones"] == 2
    assert tabla.loc["casos_nuevos", "total_restado"] == -7762
    assert tabla.loc["casos_nuevos", "mayor_estado"] == "MA"


def test_diferencia_totales_compara_con_el_ultimo_acumulado():
    """Compara la suma de incrementos con el último acumulado de cada estado."""
    df = pd.DataFrame({
        "estado": ["NY"] * 3,
        "fecha": pd.to_datetime(["2020-03-01", "2020-03-02", "2020-03-03"]),
        "casos_nuevos": [10, 5, np.nan],   # el -1 de la corrección ya es NaN
        "casos_acum": [10, 15, 14],
        "muertes_nuevas": [1, 0, 1], "muertes_acum": [1, 1, 2],
        "tests_nuevos": [1, 1, 1], "tests_acum": [1, 2, 3],
    })
    tabla = diferencia_totales(df)

    assert tabla.loc["casos_nuevos", "diferencia"] == 1
    assert tabla.loc["muertes_nuevas", "diferencia"] == 0


def test_marcar_ceros_sin_publicar(datos):
    """Un 0 se marca solo si el estado ya llevaba al menos 1.000 casos."""
    ceros = marcar_ceros_sin_publicar(datos)

    # Solo el 0 de NY, que ya llevaba 1.500 casos. VT nunca llega a 1.000.
    assert ceros.tolist() == [False, False, True, False, False, False]


def test_tratar_calidad_marca_y_vacia_los_tests_imposibles(datos):
    """Añade las marcas y vacía los tests imposibles, sin tocar el resto."""
    df = tratar_calidad(datos)

    marcas = [
        "positivos_sobre_tests", "ventilador_sobre_uci",
        "recuperados_sobre_casos", "cero_sin_publicar",
    ]
    for marca in marcas:
        assert df[marca].dtype == bool
    assert np.isnan(df.loc[0, "tests_nuevos"])
    assert np.isnan(df.loc[0, "tests_acum"])
    assert df.loc[0, "casos_nuevos"] == 50                      # los casos de esa fila se conservan
    assert df.loc[1, "ventilador_actuales"] == 12               # el respirador se marca, no se toca
    assert datos.loc[0, "tests_nuevos"] == 20                   # no modifica el original
