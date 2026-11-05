"""Tests de src/poblacion.py."""

import pandas as pd
import pytest

from src import poblacion as modulo
from src.poblacion import (
    cargar_poblacion,
    por_100k,
    preparar_poblacion,
    tasas_100k_7d,
    unir_poblacion,
)


@pytest.fixture(name="censo")
def fixture_censo():
    """Imita el fichero del Census Bureau: país, región y estados mezclados (SUMLEV 10, 20 y 40)."""
    return pd.DataFrame({
        "SUMLEV": [10, 20, 40, 40, 40],
        "STATE": [0, 0, 36, 50, 72],
        "NAME": ["United States", "Northeast Region", "New York", "Vermont", "Puerto Rico"],
        "POPESTIMATE2020": [331_000_000, 57_000_000, 20_000_000, 600_000, 3_000_000],
    })


def test_cargar_poblacion_lee_el_fichero_local(tmp_path, monkeypatch):
    """Lee el fichero del censo, que está en latin-1, sin descargarlo."""
    ruta = tmp_path / "censo.csv"
    ruta.write_bytes("NAME,STATE\nPeñasco,1\n".encode("latin-1"))

    def no_descargar(*_args, **_kwargs):
        pytest.fail("no debería descargar")

    monkeypatch.setattr(modulo.requests, "get", no_descargar)

    df = cargar_poblacion(ruta)

    assert df["NAME"].iloc[0] == "Peñasco"


def test_preparar_poblacion_se_queda_con_los_estados(censo):
    """Se queda solo con las filas de estado: FIPS, nombre y población."""
    poblacion = preparar_poblacion(censo)

    assert list(poblacion.columns) == ["fips", "nombre_estado", "poblacion"]
    assert poblacion["fips"].tolist() == [36, 50, 72]
    assert poblacion.loc[poblacion["fips"] == 50, "poblacion"].item() == 600_000


def test_preparar_poblacion_rechaza_fips_repetidos(censo):
    """Un estado repetido da error."""
    repetido = pd.concat([censo, censo.iloc[[2]]])

    with pytest.raises(ValueError, match="repetidos"):
        preparar_poblacion(repetido)


def test_unir_poblacion_conserva_todas_las_filas(censo):
    """La unión no pierde filas; un territorio sin población queda en NaN."""
    covid = pd.DataFrame({"estado": ["NY", "NY", "VT", "GU"], "fips": [36, 36, 50, 66]})
    unido = unir_poblacion(covid, preparar_poblacion(censo))

    assert len(unido) == len(covid)
    assert unido["poblacion"].tolist()[:3] == [20_000_000, 20_000_000, 600_000]
    assert pd.isna(unido.loc[3, "poblacion"])   # Guam no está en la tabla: se queda sin población


def test_unir_poblacion_falla_si_la_tabla_de_poblacion_tiene_repetidos():
    """Si la tabla de población repite un estado, la unión da error."""
    covid = pd.DataFrame({"estado": ["NY"], "fips": [36]})
    poblacion = pd.DataFrame(
        {"fips": [36, 36], "nombre_estado": ["New York"] * 2, "poblacion": [1, 2]}
    )

    with pytest.raises(pd.errors.MergeError):
        unir_poblacion(covid, poblacion)


def test_por_100k():
    """Pasa a tasa por 100.000 habitantes, con números sueltos y con series."""
    assert por_100k(155, 100_000) == pytest.approx(155)
    assert por_100k(50, 1_000_000) == pytest.approx(5)
    pd.testing.assert_series_equal(por_100k(pd.Series([10.0, 20.0]), pd.Series([1000.0, 2000.0])),
                                   pd.Series([1000.0, 1000.0]))


def test_tasas_100k_7d_media_de_la_semana_por_estado():
    """Media de 7 días dentro de cada estado, por 100.000 habitantes; sin población, NaN."""
    df = pd.DataFrame({
        "estado": ["A"] * 4 + ["B"] * 4,
        "fecha": list(pd.date_range("2020-10-01", periods=4)) * 2,
        "casos_nuevos": [10, 20, 30, 40, 1000, 1000, 1000, 1000],
        "muertes_nuevas": [1] * 8,
        "hospitalizados_actuales": [5] * 8,
        "poblacion": [1_000_000] * 4 + [None] * 4,
    })
    tasas = tasas_100k_7d(df)

    a = tasas[tasas["estado"] == "A"]
    assert a["casos_100k_7d"].iloc[:3].isna().all()               # menos de 4 días con dato
    assert a["casos_100k_7d"].iloc[3] == pytest.approx(2.5)       # (10+20+30+40)/4 por 1M -> 2,5
    assert a["muertes_100k_7d"].iloc[3] == pytest.approx(0.1)
    assert tasas.loc[tasas["estado"] == "B", "casos_100k_7d"].isna().all()
