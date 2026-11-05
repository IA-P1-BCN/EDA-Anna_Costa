"""Tests de src/variables.py."""

import numpy as np
import pandas as pd
import pytest

from src.variables import (
    OLAS,
    REGION_POR_ESTADO,
    asignar_ola,
    asignar_region,
    crear_variables,
    encontrar_valle,
    letalidad_aparente,
    partes_fecha,
    positividad_7d,
)


def test_las_regiones_cubren_los_50_estados_y_dc():
    """Hay región para los 50 estados y DC."""
    assert len(REGION_POR_ESTADO) == 51
    assert REGION_POR_ESTADO["DC"] == "Sur"


def test_encontrar_valle():
    """Devuelve el día con el valor más bajo dentro del intervalo pedido."""
    serie = pd.Series([5, 3, 1, 4, 0], index=pd.date_range("2020-06-01", periods=5))

    assert encontrar_valle(serie, "2020-06-01", "2020-06-04") == pd.Timestamp("2020-06-03")


def test_partes_fecha():
    """Saca el año, el mes y la semana (que empieza en lunes) de cada fecha."""
    df = partes_fecha(pd.DataFrame({"fecha": pd.to_datetime(["2020-03-04", "2021-01-03"])}))

    assert df["año"].tolist() == [2020, 2021]
    assert df["mes"].tolist() == [3, 1]
    # La semana empieza en lunes: el miércoles 04-03-2020 es de la semana del 02-03,
    # y el domingo 03-01-2021, de la del 28-12-2020.
    assert df["semana"].tolist() == [pd.Timestamp("2020-03-02"), pd.Timestamp("2020-12-28")]


def test_asignar_ola_incluye_el_dia_de_corte():
    """El día de corte cuenta en la ola que termina, y las olas tienen orden."""
    fechas = pd.to_datetime([
        "2020-03-01", "2020-06-09", "2020-06-10", "2020-09-12", "2020-09-13", "2021-03-07",
    ])
    df = asignar_ola(pd.DataFrame({"fecha": fechas}))

    nombres = list(OLAS)
    primera, segunda, tercera = nombres[:3]
    assert df["ola"].tolist() == [primera, primera, segunda, segunda, tercera, tercera]
    assert df["ola"].cat.ordered


def test_asignar_region():
    """Cada estado recibe su región; los territorios van aparte."""
    df = asignar_region(pd.DataFrame({"estado": ["NY", "TX", "PR"]}))

    assert df["region"].tolist() == ["Noreste", "Sur", "Territorios"]


def test_positividad_7d_suma_antes_de_dividir():
    """Suma casos y tests de 7 días antes de dividir."""
    df = pd.DataFrame({"estado": "A", "fecha": pd.date_range("2020-10-01", periods=4),
                       "casos_nuevos": [10, 10, 10, 10], "tests_nuevos": [100, 0, 100, 200]})
    positividad = positividad_7d(df)

    # Cuarto día: 40 casos / 400 tests = 10 %. Con menos de 4 días no se calcula.
    assert positividad.iloc[3] == pytest.approx(0.10)
    assert positividad.iloc[:3].isna().all()


def test_positividad_7d_quita_los_valores_imposibles():
    """Una positividad de más del 100 % pasa a NaN, salvo con maximo=None."""
    df = pd.DataFrame({"estado": "A", "fecha": pd.date_range("2020-10-01", periods=4),
                       "casos_nuevos": [100] * 4, "tests_nuevos": [10] * 4})

    assert np.isnan(positividad_7d(df).iloc[3])
    assert positividad_7d(df, maximo=None).iloc[3] == pytest.approx(10)


def test_letalidad_aparente_espera_al_minimo_de_casos():
    """La letalidad no se calcula hasta que el estado llega a 1.000 casos."""
    df = pd.DataFrame({"casos_acum": [500, 2000], "muertes_acum": [50, 40]})
    letalidad = letalidad_aparente(df)

    assert np.isnan(letalidad.iloc[0])
    assert letalidad.iloc[1] == pytest.approx(0.02)


def test_crear_variables_crea_todas_las_columnas():
    """crear_variables() añade fecha, ola, región, positividad y letalidad."""
    df = pd.DataFrame({
        "estado": ["NY"] * 5, "fecha": pd.date_range("2020-06-07", periods=5),
        "casos_nuevos": [10] * 5, "tests_nuevos": [100] * 5,
        "casos_acum": [1000, 1010, 1020, 1030, 1040], "muertes_acum": [10] * 5,
    })
    resultado = crear_variables(df)

    nuevas = ["año", "mes", "semana", "ola", "region", "positividad_7d", "letalidad_aparente"]
    for columna in nuevas:
        assert columna in resultado.columns
    assert resultado["region"].unique().tolist() == ["Noreste"]
    assert resultado["ola"].astype(str).tolist()[-1] == list(OLAS)[1]
