"""Tests de src/limpieza.py."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src import limpieza
from src.limpieza import (
    COLUMNAS,
    cargar_datos,
    convertir_fecha,
    limites_iqr,
    limpiar,
    marcar_atrasos,
    marcar_correcciones,
    marcar_territorios,
    media_vecinos,
    seleccionar_y_renombrar,
)


def respuesta_falsa(contenido: bytes) -> SimpleNamespace:
    """Sustituye a la respuesta de requests: los tests no se conectan a internet."""
    return SimpleNamespace(content=contenido, raise_for_status=lambda: None)


# --- cargar_datos -------------------------------------------------------------------------------

def test_cargar_datos_lee_el_fichero_local_sin_descargar(tmp_path, monkeypatch):
    """Si el CSV ya está en disco, lo lee sin conectarse a internet."""
    ruta = tmp_path / "datos.csv"
    ruta.write_text("a,b\n1,2\n", encoding="utf-8")
    def no_descargar(*_args, **_kwargs):
        pytest.fail("no debería descargar")

    monkeypatch.setattr(limpieza.requests, "get", no_descargar)

    df = cargar_datos(ruta)

    assert df.to_dict("list") == {"a": [1], "b": [2]}


def test_cargar_datos_descarga_y_guarda_si_no_existe(tmp_path, monkeypatch):
    """Si el CSV no está, lo descarga una vez y lo guarda en la ruta pedida."""
    ruta = tmp_path / "raw" / "datos.csv"
    llamadas = []

    def get_falso(url, **_kwargs):
        llamadas.append(url)
        return respuesta_falsa(b"a,b\n3,4\n")

    monkeypatch.setattr(limpieza.requests, "get", get_falso)

    df = cargar_datos(ruta, url="https://ejemplo/datos.csv")

    assert llamadas == ["https://ejemplo/datos.csv"]
    assert ruta.exists()
    assert df.to_dict("list") == {"a": [3], "b": [4]}


# --- convertir_fecha y seleccionar_y_renombrar ---------------------------------------------------

def test_convertir_fecha_pasa_el_entero_a_fecha():
    """El entero 20200313 pasa a ser el día 13-03-2020."""
    df = convertir_fecha(pd.DataFrame({"date": [20200313, 20210307]}))

    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert list(df["date"]) == [pd.Timestamp("2020-03-13"), pd.Timestamp("2021-03-07")]


def test_convertir_fecha_no_modifica_el_original():
    """convertir_fecha() trabaja sobre una copia."""
    original = pd.DataFrame({"date": [20200313]})
    convertir_fecha(original)

    assert original["date"].iloc[0] == 20200313


def test_seleccionar_y_renombrar_deja_solo_las_columnas_utiles_en_castellano(crudo):
    """Quedan las columnas del análisis, con nombre en castellano y los valores intactos."""
    df = seleccionar_y_renombrar(crudo)

    assert list(df.columns) == list(COLUMNAS.values())
    assert "dataQualityGrade" not in df.columns
    assert df["casos_nuevos"].tolist() == crudo["positiveIncrease"].tolist()


# --- marcar_correcciones y marcar_territorios ----------------------------------------------------

def test_marcar_correcciones_pasa_los_negativos_a_nan_y_marca_la_fila(renombrado):
    """Un incremento negativo pasa a NaN y su fila queda marcada como corrección."""
    df = marcar_correcciones(renombrado)

    fila = (df["estado"] == "NY") & (df["fecha"] == "2020-03-03")
    assert df.loc[fila, "es_correccion"].item()
    assert np.isnan(df.loc[fila, "casos_nuevos"].item())
    assert df["es_correccion"].sum() == 1


def test_marcar_correcciones_no_toca_los_acumulados_ni_los_positivos(renombrado):
    """Los acumulados y los incrementos positivos no cambian."""
    df = marcar_correcciones(renombrado)

    pd.testing.assert_series_equal(df["casos_acum"], renombrado["casos_acum"])
    assert (df["casos_nuevos"].dropna() >= 0).all()
    assert df["casos_nuevos"].notna().sum() == len(df) - 1


def test_marcar_territorios(renombrado):
    """Guam se marca como territorio; Nueva York y Vermont, no."""
    df = marcar_territorios(renombrado)

    assert df.loc[df["estado"] == "GU", "es_territorio"].all()
    assert not df.loc[df["estado"].isin(["NY", "VT"]), "es_territorio"].any()


# --- limites_iqr y media_vecinos ------------------------------------------------------------------

def test_limites_iqr():
    """Con k = 1,5 los límites son Q1 - 1,5 * IQR y Q3 + 1,5 * IQR."""
    inferior, superior = limites_iqr(pd.Series([1, 2, 3, 4, 5]))

    # Q1 = 2, Q3 = 4, IQR = 2
    assert inferior == pytest.approx(-1)
    assert superior == pytest.approx(7)


def test_limites_iqr_con_otro_k():
    """El multiplicador k se puede cambiar."""
    _, superior = limites_iqr(pd.Series([1, 2, 3, 4, 5]), k=3)

    assert superior == pytest.approx(10)


def test_media_vecinos_no_cuenta_el_propio_dia():
    """La media de los vecinos deja fuera el propio día."""
    vecinos = media_vecinos(pd.Series([1.0, 2.0, 30.0, 4.0, 5.0]), ventana=3)

    # El 30 no entra en su propia media: (2 + 4) / 2 = 3.
    assert vecinos.iloc[2] == pytest.approx(3)
    # En los extremos solo hay un vecino.
    assert vecinos.iloc[0] == pytest.approx(2)
    assert vecinos.iloc[4] == pytest.approx(4)


def test_media_vecinos_ignora_los_nan():
    """Los días sin dato no cuentan en la media de los vecinos."""
    vecinos = media_vecinos(pd.Series([1.0, np.nan, 5.0, 3.0, 1.0]), ventana=3)

    assert vecinos.iloc[2] == pytest.approx(3)   # (NaN, 3) -> solo cuenta el 3


# --- marcar_atrasos -------------------------------------------------------------------------------

def test_marcar_atrasos_marca_un_pico_aislado(serie_estado):
    """Un día con 20 veces lo normal se marca como atraso."""
    valores = [10] * 30
    valores[15] = 200
    df = marcar_atrasos(serie_estado("OH", valores))

    assert df["atraso_casos"].sum() == 1
    assert df.loc[df["atraso_casos"], "fecha"].item() == pd.Timestamp("2020-10-16")


def test_marcar_atrasos_no_marca_una_subida_gradual(serie_estado):
    """Una ola que crece poco a poco no es un atraso."""
    df = marcar_atrasos(serie_estado("TX", list(range(10, 400, 13))))

    assert not df["atraso_casos"].any()


def test_marcar_atrasos_respeta_el_minimo_en_estados_pequenos(serie_estado):
    """Un salto pequeño en valor absoluto no se marca aunque multiplique a sus vecinos."""
    valores = [1] * 30
    valores[15] = 6   # multiplica por 6 a sus vecinos, pero no llega al mínimo de 20
    df = marcar_atrasos(serie_estado("VT", valores))

    assert not df["atraso_casos"].any()


def test_marcar_atrasos_compara_cada_estado_consigo_mismo(serie_estado):
    """Lo que es normal en un estado grande puede ser un pico en uno pequeño."""
    # 200 sería normal en el estado grande, pero es un pico en el pequeño.
    grande = serie_estado("CA", [200] * 30)
    valores = [10] * 30
    valores[10] = 200
    pequeno = serie_estado("RI", valores)
    df = marcar_atrasos(pd.concat([grande, pequeno]))

    assert df.loc[df["estado"] == "RI", "atraso_casos"].sum() == 1
    assert not df.loc[df["estado"] == "CA", "atraso_casos"].any()


def test_marcar_atrasos_no_cambia_los_valores(serie_estado):
    """marcar_atrasos() solo añade la marca: los valores no cambian."""
    valores = [10] * 30
    valores[15] = 200
    df = marcar_atrasos(serie_estado("OH", valores))

    assert df["casos_nuevos"].tolist() == valores


# --- limpiar --------------------------------------------------------------------------------------

def test_limpiar_aplica_todos_los_pasos(crudo):
    """limpiar() hace todos los pasos sin perder filas."""
    df = limpiar(crudo)

    assert len(df) == len(crudo)
    nuevas = [
        "fecha", "casos_nuevos", "es_correccion", "es_territorio", "atraso_casos", "atraso_muertes",
    ]
    for columna in nuevas:
        assert columna in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["fecha"])
    assert df["es_correccion"].sum() == 1
    assert df["es_territorio"].sum() == 3


def test_limpiar_ordena_por_estado_y_fecha(crudo):
    """El resultado sale ordenado por estado y fecha, con el índice de 0 a n."""
    df = limpiar(crudo.sample(frac=1, random_state=0))

    assert df["estado"].tolist() == ["GU"] * 3 + ["NY"] * 3 + ["VT"] * 3
    assert df.groupby("estado")["fecha"].apply(lambda s: s.is_monotonic_increasing).all()
    assert df.index.tolist() == list(range(len(df)))
