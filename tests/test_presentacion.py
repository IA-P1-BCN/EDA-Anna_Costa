"""Tests de src/presentacion.py: cifras del hallazgo principal y duración del guion."""

import numpy as np
import pandas as pd
import pytest

from src.presentacion import (DIAPOSITIVAS, DURACION_MAXIMA, dia_mes, dia_mes_largo, guiones,
                              indicadores, mejor_desfase, minutos, picos, reloj, tiempos)


@pytest.fixture(name="cifras")
def fixture_cifras():
    """Las cifras que usa el guion, con valores parecidos a los reales."""
    return {
        "total_casos": 28_652_670,
        "total_muertes": 513_972,
        "por_ola": pd.DataFrame({"muertes": [107_925, 77_751, 328_296],
                                 "pico_muertes": [2112, 1142, 3334],
                                 "pico_positividad": [21.2, 7.8, 13.8]}),
        "desfase_hosp": (3, 0.95),
        "desfase_muertes": (11, 0.90),
        "desfase_casos_muertes": (20, 0.83),
        "picos_ejemplo": {"casos": pd.Timestamp("2020-07-16"),
                          "hospitalizados": pd.Timestamp("2020-07-21"),
                          "muertes": pd.Timestamp("2020-08-05")},
        "picos_regiones": pd.Series(
            pd.to_datetime(["2021-01-10", "2020-12-02", "2021-01-14", "2021-01-12"]),
            index=["Noreste", "Medio Oeste", "Sur", "Oeste"]),
    }


def test_mejor_desfase_encuentra_el_retraso():
    """Si las muertes copian a los hospitalizados con 6 días de retraso, el desfase es 6."""
    dias = pd.date_range("2020-04-01", periods=120)
    filas = []
    for estado, fase in [("AA", 0.0), ("BB", 1.5)]:
        hosp = 100 + 50 * np.sin(np.arange(120) / 9 + fase)
        filas.append(pd.DataFrame({"estado": estado, "fecha": dias, "hospitalizados": hosp,
                                   "muertes": pd.Series(hosp).shift(6).to_numpy()}))
    datos = pd.concat(filas, ignore_index=True)

    desfase, correlacion = mejor_desfase(datos, "hospitalizados", "muertes", maximo=15)

    assert desfase == 6
    assert correlacion == pytest.approx(1)


def test_indicadores_media_de_7_dias_con_toda_la_serie():
    """La media se calcula antes de recortar: el primer día del periodo ya tiene valor."""
    estados = pd.DataFrame({
        "estado": "AA", "fecha": pd.date_range("2020-03-25", periods=14),
        "casos_nuevos": range(14), "muertes_nuevas": 1.0, "hospitalizados_actuales": 5.0,
    })
    datos = indicadores(estados, desde="2020-04-01")

    assert datos["fecha"].min() == pd.Timestamp("2020-04-01")
    assert datos["casos"].iloc[0] == pytest.approx(np.mean(range(1, 8)))   # 26-03 a 01-04


def test_picos_da_la_fecha_del_maximo_de_cada_columna():
    """Una fecha por indicador."""
    serie = pd.DataFrame({"casos": [1, 5, 2], "muertes": [0, 1, 3]},
                         index=pd.date_range("2020-07-01", periods=3))
    assert picos(serie) == {"casos": pd.Timestamp("2020-07-02"),
                            "muertes": pd.Timestamp("2020-07-03")}


def test_fechas_y_tiempos_en_castellano():
    """Formatos que se ven en las diapositivas y en el guion."""
    assert dia_mes("2020-08-05") == "5 ago"
    assert dia_mes_largo("2020-12-02") == "2 de diciembre"
    assert reloj(1.75) == "1:45"
    assert minutos("una " * 130) == pytest.approx(1)


def test_el_guion_cabe_en_cinco_minutos(cifras):
    """Un texto por diapositiva, con las cifras dentro y sin pasar de 5 minutos."""
    textos = guiones(cifras)

    assert len(textos) == len(DIAPOSITIVAS)
    assert sum(minutos(t) for t in textos) <= DURACION_MAXIMA
    assert "3 días" in textos[4] and "11 días" in textos[4]
    assert "15 días después que los hospitales" in textos[5]
    assert "Medio Oeste" in textos[7] and "6 semanas" in textos[7]


def test_tabla_de_tiempos_para_ensayar(cifras):
    """Una fila por diapositiva; la última acaba en la duración total."""
    textos = guiones(cifras)
    filas = tiempos(textos)

    assert [fila[0] for fila in filas] == list(range(1, len(DIAPOSITIVAS) + 1))
    assert filas[0][1] == "Portada"
    assert filas[-1][3] == reloj(sum(minutos(t) for t in textos))
