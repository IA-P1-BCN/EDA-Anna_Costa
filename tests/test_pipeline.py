"""Tests de src/pipeline.py: el pipeline completo sobre los datos de ejemplo de conftest.py."""

from types import SimpleNamespace

import pandas as pd
import pytest

from src import limpieza, pipeline, poblacion
from src.pipeline import ORIGINALES, SALIDAS, ejecutar

CENSO_CSV = (
    "SUMLEV,STATE,NAME,POPESTIMATE2020\n"
    "10,0,United States,331000000\n"
    "40,36,New York,20000000\n"
    "40,50,Vermont,600000\n"
)


@pytest.fixture(name="carpetas")
def fixture_carpetas(tmp_path, crudo, monkeypatch):
    """data/raw/ con los dos originales ya descargados; data/processed/ todavía no existe."""
    raw = tmp_path / "raw"
    raw.mkdir()
    crudo.to_csv(raw / ORIGINALES["covid"], index=False)
    (raw / ORIGINALES["censo"]).write_bytes(CENSO_CSV.encode("latin-1"))

    def no_descargar(*_args, **_kwargs):
        pytest.fail("no debería descargar")

    monkeypatch.setattr(limpieza.requests, "get", no_descargar)
    monkeypatch.setattr(poblacion.requests, "get", no_descargar)
    return raw, tmp_path / "processed"


def test_genera_los_cuatro_ficheros(carpetas, crudo):
    """Con un solo comando salen los cuatro CSV de data/processed/, sin perder filas."""
    raw, processed = carpetas
    rutas = ejecutar(raw, processed)

    assert set(rutas) == set(SALIDAS)
    for nombre, ruta in rutas.items():
        assert ruta == processed / SALIDAS[nombre]
        assert len(pd.read_csv(ruta)) == len(crudo)


def test_cada_paso_suma_sus_columnas(carpetas):
    """Cada fichero tiene las columnas del anterior más las de su paso."""
    rutas = ejecutar(*carpetas)
    columnas = {nombre: set(pd.read_csv(ruta, nrows=0).columns) for nombre, ruta in rutas.items()}

    assert columnas["limpio"] < columnas["variables"] < columnas["poblacion"] < columnas["final"]
    assert {"ola", "region", "positividad_7d"} <= columnas["variables"]
    assert {"poblacion", "casos_100k_7d", "muertes_100k_7d"} <= columnas["poblacion"]
    assert {"positivos_sobre_tests", "cero_sin_publicar"} <= columnas["final"]


def test_los_notebooks_pueden_leer_la_salida(carpetas):
    """El fichero final se lee igual que en el notebook 07, con las fechas como fechas."""
    rutas = ejecutar(*carpetas)
    final = pd.read_csv(rutas["final"], parse_dates=["fecha", "semana"])

    assert pd.api.types.is_datetime64_any_dtype(final["fecha"])
    assert final.loc[final["estado"] == "NY", "poblacion"].eq(20_000_000).all()
    assert final.loc[final["estado"] == "GU", "poblacion"].isna().all()   # Guam no está en el censo


def test_no_escribe_nada_si_los_datos_no_son_validos(carpetas, crudo):
    """Si los datos limpios no pasan validar_limpios(), se para antes de guardar."""
    raw, processed = carpetas
    pd.concat([crudo, crudo.iloc[[0]]]).to_csv(raw / ORIGINALES["covid"], index=False)

    with pytest.raises(ValueError, match="repetid"):
        ejecutar(raw, processed)
    assert not processed.exists()


def test_descargar_vuelve_a_bajar_los_originales(carpetas, crudo, monkeypatch):
    """Con descargar=True baja otra vez los dos ficheros aunque ya estén en data/raw/."""
    raw, processed = carpetas
    descargas = []

    def get_falso(url, **_kwargs):
        descargas.append(url)
        contenido = CENSO_CSV.encode("latin-1") if url == poblacion.URL_POBLACION else (
            crudo.to_csv(index=False).encode("utf-8"))
        return SimpleNamespace(content=contenido, raise_for_status=lambda: None)

    monkeypatch.setattr(limpieza.requests, "get", get_falso)
    monkeypatch.setattr(poblacion.requests, "get", get_falso)

    ejecutar(raw, processed, descargar=True)

    assert descargas == [limpieza.URL_DATOS, poblacion.URL_POBLACION]
    assert (processed / SALIDAS["final"]).exists()


def test_main_acepta_la_opcion_descargar(monkeypatch):
    """`python -m src.pipeline --descargar` pasa la opción a ejecutar()."""
    llamadas = []
    monkeypatch.setattr(pipeline, "ejecutar", lambda **opciones: llamadas.append(opciones))

    pipeline.main([])
    pipeline.main(["--descargar"])

    assert llamadas == [{"descargar": False}, {"descargar": True}]
