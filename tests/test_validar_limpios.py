"""Tests de validar_limpios(), escritos antes que la función.

validar_limpios() comprueba que los datos limpios cumplen las reglas que el resto del
análisis da por hechas:
- están todas las columnas que deja limpiar(),
- no hay dos filas del mismo estado y día,
- no quedan incrementos diarios negativos,
- cada estado tiene todos los días entre su primera y su última fecha.

Si algo falla, lanza ValueError con todos los problemas encontrados. Si no, devuelve los
datos tal cual.
"""

import pandas as pd
import pytest

from src.limpieza import limpiar, validar_limpios


@pytest.fixture(name="limpios")
def fixture_limpios(crudo):
    """Los datos de ejemplo después de pasar por limpiar()."""
    return limpiar(crudo)


def test_datos_correctos_se_devuelven_sin_cambios(limpios):
    """Si los datos son correctos, se devuelven tal cual."""
    resultado = validar_limpios(limpios)

    pd.testing.assert_frame_equal(resultado, limpios)


def test_detecta_filas_repetidas(limpios):
    """Dos filas del mismo estado y día dan error."""
    con_repetida = pd.concat([limpios, limpios.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="repetid"):
        validar_limpios(con_repetida)


def test_detecta_incrementos_negativos(limpios):
    """Un incremento negativo que no sea NaN da error."""
    limpios.loc[0, "muertes_nuevas"] = -3

    with pytest.raises(ValueError, match="negativ"):
        validar_limpios(limpios)


def test_detecta_dias_que_faltan(limpios):
    """Si a un estado le falta un día, el error dice qué estado es."""
    sin_un_dia = limpios[~((limpios["estado"] == "NY") & (limpios["fecha"] == "2020-03-02"))]

    with pytest.raises(ValueError, match="NY"):
        validar_limpios(sin_un_dia)


def test_detecta_columnas_que_faltan(limpios):
    """Si falta una columna, el error dice cuál."""
    sin_columna = limpios.drop(columns="es_correccion")

    with pytest.raises(ValueError, match="es_correccion"):
        validar_limpios(sin_columna)


def test_informa_de_todos_los_problemas_a_la_vez(limpios):
    """Con varios problemas, el error los nombra todos, no solo el primero."""
    limpios.loc[0, "casos_nuevos"] = -1
    con_repetida = pd.concat([limpios, limpios.iloc[[3]]], ignore_index=True)

    with pytest.raises(ValueError) as error:
        validar_limpios(con_repetida)

    assert "repetid" in str(error.value)
    assert "negativ" in str(error.value)


def test_los_nan_no_cuentan_como_negativos(limpios):
    """Las correcciones, que limpiar() ya deja en NaN, no dan error."""
    assert limpios["casos_nuevos"].isna().any()

    validar_limpios(limpios)
