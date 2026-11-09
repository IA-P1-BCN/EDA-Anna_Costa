"""Estilo común de los gráficos del proyecto."""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Un color fijo por magnitud en todos los notebooks.
AZUL = "#2a78d6"      # casos
NARANJA = "#eb6834"   # muertes
VERDE = "#1baf7a"     # hospitalizados
AMARILLO = "#eda100"  # positividad (poco contraste sobre fondo claro: siempre con etiqueta directa)
GRIS = "#b9b8b2"      # contexto / resto
TEXTO = "#0b0b0b"
TEXTO_SUAVE = "#52514e"
REJILLA = "#e4e3df"
FONDO = "#fcfcfb"

# Miles con punto, como se escribe en castellano.
miles = mticker.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", "."))


def aplicar_estilo() -> None:
    """Fondo claro, rejilla discreta y títulos alineados a la izquierda."""
    plt.rcParams.update({
        "figure.figsize": (10, 4.5),
        "figure.dpi": 110,
        "figure.facecolor": FONDO,
        "axes.facecolor": FONDO,
        "axes.edgecolor": REJILLA,
        "axes.labelcolor": TEXTO_SUAVE,
        "axes.titlecolor": TEXTO,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": REJILLA,
        "grid.linewidth": 0.8,
        "xtick.color": TEXTO_SUAVE,
        "ytick.color": TEXTO_SUAVE,
        "legend.frameon": False,
        "lines.linewidth": 2,
    })


def formato_miles(numero: float) -> str:
    """12345.6 -> '12.346'."""
    return f"{numero:,.0f}".replace(",", ".")


def lineas_olas(ax, cortes) -> None:
    """Dibuja una línea discontinua en cada fecha de corte entre olas."""
    for fecha in cortes:
        ax.axvline(fecha, color=TEXTO_SUAVE, linewidth=1, linestyle="--", zorder=1)
