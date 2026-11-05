"""Tests de src/poblacion.py."""

import pandas as pd
import pytest

from src import poblacion as modulo
from src.poblacion import cargar_poblacion, por_100k, preparar_poblacion, unir_poblacion


@pytest.fixture
def censo():
    """Imita el fichero del Census Bureau: país, región y estados mezclados (SUMLEV 10, 20 y 40)."""
    return pd.DataFrame({
        "SUMLEV": [10, 20, 40, 40, 40],
        "STATE": [0, 0, 36, 50, 72],
        "NAME": ["United States", "Northeast Region", "New York", "Vermont", "Puerto Rico"],
        "POPESTIMATE2020": [331_000_000, 57_000_000, 20_000_000, 600_000, 3_000_000],
    })


def test_cargar_poblacion_lee_el_fichero_local(tmp_path, monkeypatch):
    ruta = tmp_path / "censo.csv"
    ruta.write_bytes("NAME,STATE\nPeñasco,1\n".encode("latin-1"))   # el fichero real no está en UTF-8
    monkeypatch.setattr(modulo.requests, "get", lambda *a, **k: pytest.fail("no debería descargar"))

    df = cargar_poblacion(ruta)

    assert df["NAME"].iloc[0] == "Peñasco"


def test_preparar_poblacion_se_queda_con_los_estados(censo):
    poblacion = preparar_poblacion(censo)

    assert list(poblacion.columns) == ["fips", "nombre_estado", "poblacion"]
    assert poblacion["fips"].tolist() == [36, 50, 72]
    assert poblacion.loc[poblacion["fips"] == 50, "poblacion"].item() == 600_000


def test_preparar_poblacion_rechaza_fips_repetidos(censo):
    repetido = pd.concat([censo, censo.iloc[[2]]])

    with pytest.raises(ValueError, match="repetidos"):
        preparar_poblacion(repetido)


def test_unir_poblacion_conserva_todas_las_filas(censo):
    covid = pd.DataFrame({"estado": ["NY", "NY", "VT", "GU"], "fips": [36, 36, 50, 66]})
    unido = unir_poblacion(covid, preparar_poblacion(censo))

    assert len(unido) == len(covid)
    assert unido["poblacion"].tolist()[:3] == [20_000_000, 20_000_000, 600_000]
    assert pd.isna(unido.loc[3, "poblacion"])   # Guam no está en la tabla: se queda sin población


def test_unir_poblacion_falla_si_la_tabla_de_poblacion_tiene_repetidos():
    covid = pd.DataFrame({"estado": ["NY"], "fips": [36]})
    poblacion = pd.DataFrame({"fips": [36, 36], "nombre_estado": ["New York"] * 2, "poblacion": [1, 2]})

    with pytest.raises(pd.errors.MergeError):
        unir_poblacion(covid, poblacion)


def test_por_100k():
    assert por_100k(155, 100_000) == pytest.approx(155)
    assert por_100k(50, 1_000_000) == pytest.approx(5)
    pd.testing.assert_series_equal(por_100k(pd.Series([10.0, 20.0]), pd.Series([1000.0, 2000.0])),
                                   pd.Series([1000.0, 1000.0]))
