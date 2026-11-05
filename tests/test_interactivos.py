"""Tests de src/interactivos.py."""

import plotly.graph_objects as go
import plotly.io as pio

from src.interactivos import guardar_html, registrar_plantilla


def test_registrar_plantilla_usa_separadores_en_castellano():
    registrar_plantilla()

    assert pio.templates.default == "plotly_white+eda"
    assert pio.templates["eda"].layout.separators == ",."


def test_guardar_html_pone_idioma_y_titulo(tmp_path):
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    ruta = guardar_html(fig, tmp_path / "sub" / "grafico.html", "Muertes por región & ola")

    html = ruta.read_text(encoding="utf-8")
    assert '<html lang="es">' in html
    assert "<title>Muertes por región &amp; ola</title>" in html   # el & se escapa
    assert "cdn.plot.ly" in html   # plotly.js no va dentro del fichero
