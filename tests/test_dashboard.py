"""Tests de src/dashboard.py: filtros y tablas del dashboard, sin Streamlit."""

import numpy as np
import pandas as pd
import pytest

from src.dashboard import (cargar_final, estados_de, filtrar, hospitalizados_por_region,
                           marcas_fecha, ranking_100k, resumen, serie_diaria, tabla_datos)
from src.pipeline import SALIDAS


@pytest.fixture(name="final")
def fixture_final():
    """Dos días de dos estados del Noreste, uno del Sur y Guam (sin población)."""
    estados = ["NY", "VT", "TX", "GU"]
    return pd.DataFrame({
        "fecha": pd.to_datetime(["2020-04-01"] * 4 + ["2020-04-02"] * 4),
        "estado": estados * 2,
        "nombre_estado": ["New York", "Vermont", "Texas", np.nan] * 2,
        "region": ["Noreste", "Noreste", "Sur", "Territorios"] * 2,
        "poblacion": [20_000_000, 600_000, 29_000_000, np.nan] * 2,
        "casos_nuevos": [1000, 10, 500, 5, 3000, 20, 700, 5],
        "muertes_nuevas": [100, 1, 10, 0, 200, 0, 20, 0],
        "hospitalizados_actuales": [4000, np.nan, 1000, np.nan, 6000, 30, 2000, np.nan],
        "casos_100k_7d": np.nan, "muertes_100k_7d": np.nan, "positividad_7d": np.nan,
    })


def test_filtrar_por_region_estado_y_fechas(final):
    """Sin estados elegidos entran todos los de la región; con estados, solo esos."""
    noreste = filtrar(final, ["Noreste"], [], "2020-04-01", "2020-04-02")
    assert set(noreste["estado"]) == {"NY", "VT"}
    assert len(noreste) == 4

    solo_ny = filtrar(final, ["Noreste", "Sur"], ["NY"], "2020-04-02", "2020-04-02")
    assert solo_ny["estado"].tolist() == ["NY"]
    assert filtrar(final, [], [], "2020-04-01", "2020-04-02").empty


def test_estados_de_ordena_por_nombre_y_usa_el_codigo_si_no_hay_nombre(final):
    """Las opciones del filtro de estados salen de las regiones elegidas."""
    assert estados_de(final, ["Noreste", "Territorios"]) == {
        "GU": "GU (GU)", "NY": "New York (NY)", "VT": "Vermont (VT)"}


def test_resumen_tasas_solo_con_estados_con_poblacion(final):
    """Los totales cuentan todo; la tasa por 100.000 deja fuera a Guam, que no tiene población."""
    cifras = resumen(final)

    assert cifras["casos"] == 5240
    assert cifras["muertes"] == 331
    assert cifras["muertes_100k"] == pytest.approx(331 / 49_600_000 * 100_000)
    assert cifras["pico_hospitalizados"] == 8030
    assert cifras["fecha_pico"] == pd.Timestamp("2020-04-02")


def test_resumen_sin_poblacion_no_da_tasa(final):
    """Si solo se elige Guam, no hay tasa por habitante que calcular."""
    cifras = resumen(final[final["estado"] == "GU"])
    assert cifras["muertes_100k"] is None
    assert cifras["casos"] == 10


def test_serie_diaria_suma_la_seleccion(final):
    """Un valor por día con la suma de los estados elegidos."""
    serie = serie_diaria(final, "casos_nuevos")
    assert serie["diaria"].tolist() == [1515, 3725]
    assert serie["media_7d"].isna().all()   # hacen falta al menos 4 días


def test_ranking_100k_de_mayor_a_menor_sin_territorios(final):
    """Casos del periodo por 100.000 habitantes; Guam no sale porque no tiene población."""
    ranking = ranking_100k(final, "casos_nuevos")

    assert ranking["estado"].tolist() == ["NY", "VT", "TX"]
    assert ranking.loc[0, "por_100k"] == pytest.approx(4000 / 20_000_000 * 100_000)
    assert ranking.loc[0, "total"] == 4000


def test_hospitalizados_por_region_divide_entre_los_que_publican(final):
    """Un estado sin dato ese día (Vermont el día 1) no cuenta en la población de su región."""
    datos = pd.concat([final.assign(fecha=final["fecha"] + pd.Timedelta(days=2 * i))
                       for i in range(2)], ignore_index=True)   # 4 días seguidos
    tasa = hospitalizados_por_region(datos)

    assert list(tasa.columns) == ["Noreste", "Sur"]
    dia_1 = 4000 / 20_000_000 * 100_000
    dia_2 = 6030 / 20_600_000 * 100_000
    assert tasa.loc["2020-04-04", "Noreste"] == pytest.approx((dia_1 + dia_2) / 2)


def test_tabla_datos_lo_mas_reciente_primero(final):
    """La tabla de la pestaña "Datos" va en castellano y empieza por el último día."""
    tabla = tabla_datos(final)
    assert tabla.columns[:3].tolist() == ["Fecha", "Estado", "Nombre"]
    assert tabla.loc[0, "Fecha"] == pd.Timestamp("2020-04-02")
    assert len(tabla) == len(final)


@pytest.mark.parametrize(("desde", "hasta", "esperado"), [
    ("2020-01-13", "2021-03-07",
     ["feb 2020", "abr 2020", "jun 2020", "ago 2020", "oct 2020", "dic 2020", "feb 2021"]),
    ("2020-11-05", "2020-11-12",
     ["5 nov", "6 nov", "7 nov", "8 nov", "9 nov", "10 nov", "11 nov", "12 nov"]),
])
def test_marcas_fecha_en_castellano(desde, hasta, esperado):
    """Meses en castellano; en periodos cortos, días."""
    marcas, etiquetas = marcas_fecha(desde, hasta)
    assert etiquetas == esperado
    assert all(pd.Timestamp(desde) <= marca <= pd.Timestamp(hasta) for marca in marcas)


def test_cargar_final_ejecuta_el_pipeline_si_falta_el_fichero(carpeta_raw, tmp_path):
    """En un servidor recién arrancado no hay data/processed/: se genera con el pipeline."""
    processed = tmp_path / "processed"
    final = cargar_final(processed, carpeta_raw)

    assert (processed / SALIDAS["final"]).exists()
    assert pd.api.types.is_datetime64_any_dtype(final["fecha"])
    assert {"region", "poblacion", "casos_100k_7d"} <= set(final.columns)
