"""Tests de src/transformaciones.py."""

import numpy as np
import pandas as pd
import pytest

from src.transformaciones import asimetria, efecto_dia_semana, log10_1p, media_movil


def test_media_movil_se_calcula_dentro_de_cada_estado():
    df = pd.DataFrame({
        "estado": ["A"] * 5 + ["B"] * 5,
        "fecha": list(pd.date_range("2020-10-01", periods=5)) * 2,
        "casos": [1, 2, 3, 4, 5, 100, 100, 100, 100, 100],
    })
    resultado = media_movil(df, ["casos"], ventana=3, minimo=2)

    a = resultado[resultado["estado"] == "A"]["casos_7d"].tolist()
    b = resultado[resultado["estado"] == "B"]["casos_7d"].tolist()
    assert np.isnan(a[0])                        # un solo día: no llega al mínimo
    assert a[1:] == pytest.approx([1.5, 2, 3, 4])
    assert b[1:] == pytest.approx([100] * 4)     # B no arrastra los valores de A


def test_media_movil_acepta_huecos_si_hay_dias_suficientes():
    df = pd.DataFrame({"estado": "A", "fecha": pd.date_range("2020-10-01", periods=7),
                       "casos": [7, 7, 7, np.nan, 7, 7, 7]})
    resultado = media_movil(df, ["casos"])

    assert resultado["casos_7d"].iloc[-1] == pytest.approx(7)


def test_efecto_dia_semana_detecta_los_lunes_bajos():
    fechas = pd.date_range("2020-10-05", periods=70)   # empieza en lunes, diez semanas completas
    valores = np.where(fechas.day_of_week == 0, 50.0, 100.0)
    efecto = efecto_dia_semana(pd.Series(valores, index=fechas))

    assert list(efecto.index) == ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    assert efecto["lunes"] < 0.6
    assert efecto["jueves"] > 1


def test_log10_1p_admite_ceros():
    assert log10_1p(np.array([0, 9, 99])) == pytest.approx([0, 1, 2])


def test_asimetria_baja_con_el_logaritmo():
    sesgada = pd.DataFrame({"x": [1, 1, 2, 2, 3, 3, 4, 5, 10, 100, 1000]})
    tabla = asimetria(sesgada, ["x"])

    assert tabla.loc["x", "asimetria_original"] > 2
    assert abs(tabla.loc["x", "asimetria_log"]) < tabla.loc["x", "asimetria_original"]
