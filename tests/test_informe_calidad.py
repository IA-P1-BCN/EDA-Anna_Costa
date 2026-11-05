"""Tests de src/informe_calidad.py: las cifras del informe de calidad y el fichero que genera."""

import numpy as np
import pandas as pd

from src.informe_calidad import (agrupar_descartadas, generar, nulos_por_posicion, numero,
                                 peso_atrasos, porcentaje)


def test_numero_y_porcentaje_en_castellano():
    """Miles con punto, decimales con coma y una raya cuando no hay dato."""
    assert numero(1234567) == "1.234.567"
    assert numero(-7757.25, 1) == "-7.757,2"
    assert numero(np.nan) == "—"
    assert porcentaje(16.63) == "16,6 %"
    assert porcentaje(np.nan) == "—"


def test_agrupar_descartadas_por_motivo(crudo):
    """Cada columna que no se conserva cae en un solo grupo, según lo que contiene."""
    crudo = crudo.assign(grade=np.nan, score=0, posNeg=1, hash="abc", negative=5)
    grupos = agrupar_descartadas(crudo)

    assert grupos["Vacías al 100 %"] == ["grade"]
    assert grupos["Siempre valen 0 (la fuente las daba por obsoletas)"] == ["score"]
    assert grupos["Repiten otra columna"] == ["posNeg"]
    assert grupos["Metadatos de la API (cuándo se actualizó el registro)"] == ["hash"]
    assert grupos["Demasiados nulos o una unidad distinta en cada estado"] == [
        "dataQualityGrade", "negative"]


def test_nulos_por_posicion_separa_el_principio_de_los_huecos():
    """Un nulo antes del primer dato del estado no es un hueco; uno después, sí."""
    df = pd.DataFrame({
        "estado": ["A"] * 5 + ["B"] * 2,
        "fecha": [*pd.date_range("2020-03-01", periods=5), *pd.date_range("2020-03-01", periods=2)],
        "valor": [np.nan, np.nan, 1, np.nan, 2, np.nan, np.nan],   # B no publica nunca
    })
    resultado = nulos_por_posicion(df, ["valor"]).loc["valor"]

    assert resultado["nulos"] == 5
    assert resultado["antes_del_primer_dato"] == 4
    assert resultado["despues_de_empezar"] == 1


def test_peso_atrasos_cuenta_lo_que_suman_los_dias_marcados():
    """Parte del total de la columna que está en los días marcados como atraso."""
    limpio = pd.DataFrame({
        "estado": ["A", "A", "B", "B"],
        "casos_nuevos": [10, 30, 40, 20], "muertes_nuevas": [1, 1, 1, 1],
        "hospitalizados_nuevos": [0, 0, 0, 5],
        "atraso_casos": [False, True, True, False], "atraso_muertes": False,
        "atraso_hospitalizados": False,
    })
    atrasos = peso_atrasos(limpio)

    assert atrasos.loc["atraso_casos", "filas"] == 2
    assert atrasos.loc["atraso_casos", "estados"] == 2
    assert atrasos.loc["atraso_casos", "pct_del_total"] == 70
    assert atrasos.loc["atraso_muertes", "filas"] == 0


def test_generar_escribe_el_informe_con_sus_cuatro_apartados(carpeta_raw, tmp_path):
    """El informe sale de data/raw/ y cubre faltantes, correcciones y pendientes."""
    ruta = generar(carpeta_raw, tmp_path / "reports" / "informe_calidad.md")
    texto = ruta.read_text(encoding="utf-8")

    for apartado in ["## 1. Qué faltaba", "## 2. Qué se corrigió",
                     "## 3. Qué se marcó sin cambiar el valor", "## 4. Qué quedó pendiente"]:
        assert apartado in texto
    # El ejemplo tiene un incremento negativo: NY, -1 caso el 03-03-2020.
    assert "| `casos_nuevos` | 1 | 1 | -1 | -1 (NY, 03-03-2020) |" in texto
    assert "GU no están en la tabla del US Census Bureau" in texto
