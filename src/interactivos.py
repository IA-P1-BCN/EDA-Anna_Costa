"""Estilo común y guardado de los gráficos interactivos de plotly."""

from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

from src.graficos import FONDO, REJILLA, TEXTO, TEXTO_SUAVE

# Un color por región, distinto de los de las magnitudes (azul = casos, naranja = muertes, verde = hospitalizados).
# Validados para daltonismo; el rosa y el amarillo tienen poco contraste, así que siempre van con etiqueta.
COLORES_REGION = {
    "Noreste": "#6250d6",      # violeta
    "Medio Oeste": "#e87ba4",  # rosa
    "Sur": "#008300",          # verde oscuro
    "Oeste": "#eda100",        # amarillo
}

# Rampa secuencial naranja (muertes): de casi nada a mucho.
ESCALA_MUERTES = [
    [0.0, "#fdf0e8"],
    [0.25, "#f8c6aa"],
    [0.5, "#f1915f"],
    [0.75, "#d4561f"],
    [1.0, "#8f3410"],
]


def registrar_plantilla() -> None:
    """Plantilla 'eda': fondo claro, rejilla discreta, separadores en castellano (1.234,5)."""
    pio.templates["eda"] = go.layout.Template(
        layout=dict(
            font=dict(family="DejaVu Sans, Arial, sans-serif", size=13, color=TEXTO),
            title=dict(x=0.01, xanchor="left", font=dict(size=17, color=TEXTO)),
            paper_bgcolor=FONDO,
            plot_bgcolor=FONDO,
            separators=",.",
            xaxis=dict(gridcolor=REJILLA, linecolor=REJILLA, tickfont=dict(color=TEXTO_SUAVE), zeroline=False),
            yaxis=dict(gridcolor=REJILLA, linecolor=REJILLA, tickfont=dict(color=TEXTO_SUAVE), zeroline=False),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            hoverlabel=dict(font=dict(family="DejaVu Sans, Arial, sans-serif")),
            margin=dict(l=60, r=30, t=80, b=50),
        )
    )
    pio.templates.default = "plotly_white+eda"


def guardar_html(fig: go.Figure, ruta: Path) -> Path:
    """Guarda el gráfico como página HTML independiente (plotly.js se carga desde su CDN)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(ruta, include_plotlyjs="cdn", full_html=True, config={"displaylogo": False})
    return ruta
