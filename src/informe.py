"""Genera el informe ejecutivo en PDF (reports/informe_ejecutivo.pdf).

Uso, desde la raíz del repositorio y después de ejecutar `python -m src.pipeline`
(o los notebooks 01 a 03):

    python -m src.informe

Todas las cifras del texto se calculan aquí a partir de los datos procesados.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from src.graficos import AZUL, GRIS, NARANJA, TEXTO, TEXTO_SUAVE, VERDE, aplicar_estilo, formato_miles, miles
from src.variables import OLAS, REGIONES

RAIZ = Path(__file__).resolve().parent.parent
RUTA_VARIABLES = RAIZ / "data" / "processed" / "covid_estados_variables.csv"
CARPETA = RAIZ / "reports"
FIGURAS = CARPETA / "figuras"
RUTA_PDF = CARPETA / "informe_ejecutivo.pdf"

# Población del censo de 2020 (Census Bureau), en % del total de los 50 estados y DC.
PESO_POBLACION = pd.Series({"Noreste": 17.4, "Medio Oeste": 20.8, "Sur": 38.1, "Oeste": 23.7})
NOMBRES_OLA = ["Primavera 2020", "Verano 2020", "Otoño-invierno 2020-21"]


def decimal(numero: float, decimales: int = 1) -> str:
    """5.48 -> '5,5'."""
    return f"{numero:.{decimales}f}".replace(".", ",")


def millones(numero: float) -> str:
    """28650000 -> '28,7 millones'."""
    return f"{decimal(numero / 1e6)} millones"


# ---------------------------------------------------------------- datos y cifras

def cargar() -> pd.DataFrame:
    if not RUTA_VARIABLES.exists():
        raise FileNotFoundError(f"Falta {RUTA_VARIABLES.relative_to(RAIZ)}: ejecuta antes los notebooks 01, 02 y 03.")
    datos = pd.read_csv(RUTA_VARIABLES, parse_dates=["fecha"])
    datos["ola"] = pd.Categorical(datos["ola"], categories=list(OLAS), ordered=True)
    return datos[~datos["es_territorio"]]


def serie_nacional(estados: pd.DataFrame) -> pd.DataFrame:
    suma = estados.groupby("fecha")[["casos_nuevos", "muertes_nuevas", "tests_nuevos",
                                     "hospitalizados_actuales"]].sum()
    return pd.DataFrame({
        "casos": suma["casos_nuevos"].rolling(7).mean(),
        "muertes": suma["muertes_nuevas"].rolling(7).mean(),
        "hospitalizados": suma["hospitalizados_actuales"],
        "positividad": suma["casos_nuevos"].rolling(7).sum() / suma["tests_nuevos"].rolling(7).sum() * 100,
        "casos_dia": suma["casos_nuevos"],
        "muertes_dia": suma["muertes_nuevas"],
        "tests_dia": suma["tests_nuevos"],
    })


def calcular_cifras(estados: pd.DataFrame, nacional: pd.DataFrame) -> dict:
    cortes = pd.to_datetime(list(OLAS.values()))
    tramos = [nacional.loc[:cortes[0]], nacional.loc[cortes[0] + pd.Timedelta(days=1):cortes[1]],
              nacional.loc[cortes[1] + pd.Timedelta(days=1):]]
    por_ola = pd.DataFrame({
        "casos": [t["casos_dia"].sum() for t in tramos],
        "muertes": [t["muertes_dia"].sum() for t in tramos],
        "tests": [t["tests_dia"].sum() for t in tramos],
        "pico_casos": [t["casos"].max() for t in tramos],
        "pico_muertes": [t["muertes"].max() for t in tramos],
        "pico_positividad": [t["positividad"].loc["2020-03-15":].max() for t in tramos],
    }, index=NOMBRES_OLA)
    por_ola["letalidad"] = por_ola["muertes"] / por_ola["casos"] * 100

    reparto = (estados.groupby(["ola", "region"], observed=True)["muertes_nuevas"].sum()
               .groupby(level="ola", observed=True).transform(lambda s: s / s.sum() * 100))

    invierno = nacional.loc["2020-10-01":, ["casos", "hospitalizados", "muertes"]]
    mitad = {}
    for columna in invierno:
        serie = invierno[columna]
        despues = serie.loc[serie.idxmax():]
        bajo = despues[despues <= serie.max() / 2]
        mitad[columna] = (bajo.index[0] - serie.idxmax()).days if len(bajo) else None
    return {
        "por_ola": por_ola,
        "reparto": reparto,
        "invierno": invierno,
        "mitad": mitad,
        "muertes_final_invierno": invierno["muertes"].iloc[-1] / invierno["muertes"].max() * 100,
        "total_casos": nacional["casos_dia"].sum(),
        "total_muertes": nacional["muertes_dia"].sum(),
        "fecha_pico_muertes": nacional["muertes"].idxmax(),
        "cortes": cortes[:2],
    }


# ---------------------------------------------------------------- gráficos

def guardar(fig, nombre: str) -> Path:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    ruta = FIGURAS / nombre
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return ruta


def grafico_olas(nacional: pd.DataFrame, cifras: dict) -> Path:
    serie = nacional.loc["2020-03-01":]
    fig, ejes = plt.subplots(1, 2, figsize=(10, 3.1))
    for ax, columna, color, titulo in [(ejes[0], "casos", AZUL, "Casos nuevos al día"),
                                       (ejes[1], "muertes", NARANJA, "Muertes al día")]:
        ax.fill_between(serie.index, serie[columna], color=color, alpha=0.15, linewidth=0)
        ax.plot(serie.index, serie[columna], color=color)
        for corte in cifras["cortes"]:
            ax.axvline(corte, color=TEXTO_SUAVE, linewidth=1, linestyle="--")
        pico = serie[columna].idxmax()
        ax.annotate(formato_miles(serie[columna].max()), xy=(pico, serie[columna].max()), xytext=(0, 5),
                    textcoords="offset points", ha="center", color=TEXTO, fontsize=9)
        ax.set_ylim(0, serie[columna].max() * 1.2)
        ax.set_title(titulo + " (media de 7 días)", fontsize=11)
        ax.yaxis.set_major_formatter(miles)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m-%y"))
        ax.grid(axis="x", visible=False)
        for x, texto in zip(["2020-04-20", "2020-07-25", "2020-12-10"], ["1", "2", "3"]):
            ax.text(pd.Timestamp(x), serie[columna].max() * 1.12, f"ola {texto}", ha="center", color=TEXTO_SUAVE,
                    fontsize=8)
    plt.tight_layout()
    return guardar(fig, "1_olas.png")


def grafico_regiones(cifras: dict) -> Path:
    reparto = cifras["reparto"]
    orden = list(REGIONES)[::-1]
    fig, ejes = plt.subplots(1, 3, figsize=(10, 2.7), sharex=True, sharey=True)
    for ax, ola, nombre in zip(ejes, OLAS, NOMBRES_OLA):
        valores = reparto.loc[ola].reindex(orden)
        ax.barh(orden, valores, color=NARANJA, height=0.6)
        ax.scatter(PESO_POBLACION.reindex(orden), orden, marker="|", s=300, color=TEXTO, linewidths=2, zorder=3)
        for posicion, (valor, peso) in enumerate(zip(valores, PESO_POBLACION.reindex(orden))):
            cerca = 0 < peso - valor < 10  # si la marca de población queda justo detrás, la etiqueta va tras ella
            ax.text((peso if cerca else valor) + 1.5, posicion, f"{valor:.0f} %", va="center", color=TEXTO,
                    fontsize=9)
        ax.set_title(nombre, fontsize=11)
        ax.set_xlim(0, 70)
        ax.set_axisbelow(True)
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="x", labelsize=8)
    ejes[1].set_xlabel("% de las muertes de la ola  ( | = % de la población)", fontsize=9)
    plt.tight_layout()
    return guardar(fig, "2_regiones.png")


def grafico_invierno(cifras: dict) -> Path:
    invierno = cifras["invierno"]
    indice = invierno / invierno.max() * 100
    fig, ax = plt.subplots(figsize=(10, 3.2))
    etiquetas = {"casos": ("Casos", AZUL), "hospitalizados": ("Hospitalizados", VERDE), "muertes": ("Muertes", NARANJA)}
    finales = indice.iloc[-1].sort_values()
    posiciones = {}
    for columna, valor in finales.items():
        posiciones[columna] = max(valor, max(posiciones.values(), default=-10) + 9)
    for columna, (nombre, color) in etiquetas.items():
        ax.plot(indice.index, indice[columna], color=color)
        ax.annotate(nombre, xy=(indice.index[-1], indice[columna].iloc[-1]),
                    xytext=(indice.index[-1] + pd.Timedelta(days=3), posiciones[columna]), va="center",
                    color=TEXTO, fontsize=9)
    ax.axhline(50, color=GRIS, linewidth=1)
    ax.text(indice.index[0], 51.5, "mitad del máximo", color=TEXTO_SUAVE, fontsize=8)
    ax.set_ylim(0, 108)
    ax.set_xlim(right=indice.index[-1] + pd.Timedelta(days=24))
    ax.set_ylabel("% de su máximo")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m-%y"))
    ax.set_title("Ola de otoño-invierno: cada indicador como % de su máximo", fontsize=11)
    ax.grid(axis="x", visible=False)
    plt.tight_layout()
    return guardar(fig, "3_invierno.png")


# ---------------------------------------------------------------- PDF

def registrar_fuentes() -> None:
    carpeta = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", str(carpeta / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(carpeta / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")


def estilos() -> dict:
    tinta, suave = colors.HexColor(TEXTO), colors.HexColor(TEXTO_SUAVE)
    return {
        "titulo": ParagraphStyle("titulo", fontName="DejaVu-Bold", fontSize=17, leading=21, textColor=tinta),
        "subtitulo": ParagraphStyle("subtitulo", fontName="DejaVu", fontSize=9, leading=12, textColor=suave),
        "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=11.5, leading=15, textColor=tinta,
                             spaceBefore=7, spaceAfter=2),
        "cuerpo": ParagraphStyle("cuerpo", fontName="DejaVu", fontSize=9, leading=12.5, textColor=tinta),
        "vineta": ParagraphStyle("vineta", fontName="DejaVu", fontSize=9, leading=12.5, textColor=tinta,
                                 leftIndent=10, bulletIndent=0, spaceAfter=1.5),
        "cifra": ParagraphStyle("cifra", fontName="DejaVu-Bold", fontSize=15, leading=18, textColor=tinta,
                                alignment=TA_CENTER),
        "etiqueta": ParagraphStyle("etiqueta", fontName="DejaVu", fontSize=7.5, leading=9.5, textColor=suave,
                                   alignment=TA_CENTER),
        "nota": ParagraphStyle("nota", fontName="DejaVu", fontSize=7.5, leading=10, textColor=suave),
        "celda": ParagraphStyle("celda", fontName="DejaVu", fontSize=8.5, leading=11, textColor=tinta),
    }


def vinetas(textos: list, e: dict) -> list:
    return [Paragraph(t, e["vineta"], bulletText="•") for t in textos]


def imagen(ruta: Path, ancho: float) -> Image:
    figura = Image(str(ruta))
    figura.drawWidth, figura.drawHeight = ancho, ancho * figura.imageHeight / figura.imageWidth
    return figura


def tarjetas(cifras: dict, e: dict, ancho: float) -> Table:
    por_ola = cifras["por_ola"]
    datos = [
        (millones(cifras["total_casos"]), "casos notificados"),
        (formato_miles(round(cifras["total_muertes"], -3)), "muertes"),
        (formato_miles(por_ola["pico_muertes"].max()),
         f"muertes al día en el peor momento ({cifras['fecha_pico_muertes']:%m-%Y})"),
        ("≈ 3 semanas", "entre los contagios y las muertes"),
    ]
    celdas = [[Paragraph(c, e["cifra"]) for c, _ in datos], [Paragraph(t, e["etiqueta"]) for _, t in datos]]
    tabla = Table(celdas, colWidths=[ancho / 4] * 4)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0efec")),
        ("LINEAFTER", (0, 0), (-2, -1), 2, colors.white),
        ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return tabla


def tabla_olas(cifras: dict, e: dict, ancho: float) -> Table:
    por_ola = cifras["por_ola"]
    filas = [["", *NOMBRES_OLA]]
    filas.append(["Casos al día en el pico", *[formato_miles(v) for v in por_ola["pico_casos"]]])
    filas.append(["Muertes al día en el pico", *[formato_miles(v) for v in por_ola["pico_muertes"]]])
    filas.append(["% de pruebas positivas en el pico", *[f"{decimal(v)} %" for v in por_ola["pico_positividad"]]])
    filas.append(["Muertes por cada 100 casos detectados", *[decimal(v) for v in por_ola["letalidad"]]])
    celdas = [[Paragraph(f"<b>{c}</b>" if i == 0 or j == 0 else c, e["celda"]) for j, c in enumerate(fila)]
              for i, fila in enumerate(filas)]
    tabla = Table(celdas, colWidths=[ancho * 0.37] + [ancho * 0.21] * 3)
    tabla.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(TEXTO)),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#e4e3df")),
        ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#fdeee7")),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabla


def construir_pdf(cifras: dict, figuras: dict) -> None:
    registrar_fuentes()
    e = estilos()
    margen = 1.6 * cm
    ancho = A4[0] - 2 * margen
    por_ola, reparto, mitad = cifras["por_ola"], cifras["reparto"], cifras["mitad"]
    ola1, ola2, ola3 = list(OLAS)
    invierno_vs_resto = por_ola["muertes"].iloc[2] > por_ola["muertes"].iloc[:2].sum()
    proporcion_casos = por_ola["pico_casos"].iloc[2] / por_ola["pico_casos"].iloc[0]
    proporcion_muertes = por_ola["pico_muertes"].iloc[0] / por_ola["pico_muertes"].iloc[2]

    historia = [
        Paragraph("COVID-19 en Estados Unidos: qué pasó, dónde y qué aprender", e["titulo"]),
        Spacer(1, 3),
        Paragraph("Informe ejecutivo · Enero de 2020 a marzo de 2021 · 50 estados y Washington D. C. · "
                  "Datos de The COVID Tracking Project", e["subtitulo"]),
        Spacer(1, 9),
        tarjetas(cifras, e, ancho),
        Spacer(1, 6),
        Paragraph("En resumen", e["h2"]),
        *vinetas([
            "Hubo <b>tres olas</b>, y la de otoño-invierno fue con diferencia la peor.",
            "Cada ola golpeó con más fuerza a <b>una zona distinta</b> del país.",
            "Las hospitalizaciones avisan de las muertes con <b>casi dos semanas</b> de antelación.",
            "Al principio de la pandemia solo se detectaba <b>una pequeña parte</b> de los contagios.",
        ], e),

        Paragraph("1. Tres olas, y la de otoño-invierno fue la peor", e["h2"]),
        Paragraph(
            f"Entre octubre de 2020 y marzo de 2021 se notificaron {millones(por_ola['casos'].iloc[2])} de casos y "
            f"{formato_miles(round(por_ola['muertes'].iloc[2], -3))} muertes"
            f"{', más que en las dos olas anteriores juntas' if invierno_vs_resto else ''}. En su peor momento, en "
            f"enero de 2021, hubo unos {formato_miles(round(por_ola['pico_casos'].iloc[2], -3))} casos y "
            f"{formato_miles(por_ola['pico_muertes'].iloc[2])} muertes al día.", e["cuerpo"]),
        Spacer(1, 3),
        imagen(figuras["olas"], ancho),

        Paragraph("2. Cada ola golpeó a una zona distinta", e["h2"]),
        Paragraph(
            f"En la primavera de 2020, el <b>Noreste</b> (Nueva York, Nueva Jersey…) sumó el "
            f"{reparto.loc[(ola1, 'Noreste')]:.0f} % de las muertes con solo el {decimal(PESO_POBLACION['Noreste'], 0)} % "
            f"de la población. En verano la ola se trasladó al <b>Sur</b> ({reparto.loc[(ola2, 'Sur')]:.0f} % de las "
            f"muertes). La de otoño-invierno se extendió a todo el país: cada región tuvo más o menos las muertes que "
            f"le correspondían por población. Las barras muestran qué parte de las muertes de cada ola hubo en cada "
            f"región; la marca negra, qué parte de la población vive en ella.", e["cuerpo"]),
        Spacer(1, 3),
        imagen(figuras["regiones"], ancho),
    ]

    pagina_2 = [
        Paragraph("3. Los hospitales avisan casi dos semanas antes", e["h2"]),
        Paragraph(
            "Comparando cada estado consigo mismo, las hospitalizaciones siguen a los casos con unos 3 días de "
            "retraso, y las muertes llegan unos 11 días después de las hospitalizaciones: <b>unas tres semanas "
            "desde los contagios</b>. El desfase se ve sobre todo cuando una ola baja: en el invierno, los casos "
            f"tardaron {mitad['casos']} días en caer a la mitad y las hospitalizaciones {mitad['hospitalizados']}. "
            f"Las muertes, a 7 de marzo de 2021, seguían en el {cifras['muertes_final_invierno']:.0f} % de su máximo.",
            e["cuerpo"]),
        Spacer(1, 3),
        imagen(figuras["invierno"], ancho),

        Paragraph("4. Al principio solo se veía la punta del iceberg", e["h2"]),
        Paragraph(
            f"El pico de casos del invierno fue unas {proporcion_casos:.0f} veces el de la primavera, pero el pico de "
            f"muertes de la primavera ya llegaba al {decimal(proporcion_muertes * 100, 0)} % del de invierno. La "
            "explicación son las pruebas: en la primavera de 2020 se hacían tan pocas que solo se analizaba a quien "
            "tenía síntomas claros, y una de cada cinco salía positiva. Por eso las muertes por cada 100 casos "
            "detectados eran mucho más altas: no tanto porque el virus fuera más letal, sino sobre todo porque muchos "
            "casos leves no se contaban.", e["cuerpo"]),
        Spacer(1, 4),
        tabla_olas(cifras, e, ancho),

        Paragraph("Recomendaciones", e["h2"]),
        *vinetas([
            "<b>Usar las hospitalizaciones como señal de alarma.</b> Cuando suben, preparar camas de UCI y personal "
            "para las dos semanas siguientes, sin esperar a las muertes.",
            "<b>Aumentar las pruebas cuando más del 5 % sale positivo</b> (el umbral que recomendaba la OMS): es "
            "señal de que hay contagios sin detectar.",
            "<b>Planificar por regiones.</b> Las olas no llegan a la vez a todo el país, así que el material y el "
            "personal sanitario se pueden reforzar primero donde empieza la ola.",
            "<b>Comparar estados por habitante</b> antes de decidir dónde actuar: las cifras absolutas favorecen "
            "siempre a los estados grandes.",
        ], e),

        Paragraph("Limitaciones", e["h2"]),
        *vinetas([
            "Las cifras son absolutas, no por habitante; los estados más poblados pesan más.",
            "En la primavera de 2020 se hacían pocas pruebas: los casos de la primera ola están muy por debajo de "
            "los reales.",
            "Cada estado contaba las pruebas y las hospitalizaciones a su manera, y algunos días incluyen datos "
            "atrasados de semanas anteriores.",
            "Los datos terminan el 7 de marzo de 2021, cuando el proyecto dejó de recogerlos.",
        ], e),
        Spacer(1, 8),
        Paragraph("Fuente: The COVID Tracking Project (The Atlantic), licencia CC BY 4.0. Población: censo de EE. UU. "
                  "de 2020. Cifras de los 50 estados y Washington D. C.; medias de 7 días para suavizar el efecto de "
                  "los fines de semana. Análisis completo en los notebooks del repositorio.", e["nota"]),
    ]

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(colors.HexColor(TEXTO_SUAVE))
        canvas.drawString(margen, 1 * cm, "COVID-19 en Estados Unidos · Informe ejecutivo")
        canvas.drawRightString(A4[0] - margen, 1 * cm, f"Página {doc.page}")
        canvas.restoreState()

    CARPETA.mkdir(parents=True, exist_ok=True)
    documento = SimpleDocTemplate(str(RUTA_PDF), pagesize=A4, leftMargin=margen, rightMargin=margen,
                                  topMargin=1.4 * cm, bottomMargin=1.6 * cm,
                                  title="COVID-19 en Estados Unidos: informe ejecutivo", author="Anna Costa")
    documento.build(historia + [PageBreak()] + [KeepTogether(pagina_2[:3])] + pagina_2[3:],
                    onFirstPage=pie, onLaterPages=pie)


def main() -> None:
    aplicar_estilo()
    estados = cargar()
    nacional = serie_nacional(estados)
    cifras = calcular_cifras(estados, nacional)
    figuras = {
        "olas": grafico_olas(nacional, cifras),
        "regiones": grafico_regiones(cifras),
        "invierno": grafico_invierno(cifras),
    }
    construir_pdf(cifras, figuras)
    print("Informe guardado en", RUTA_PDF.relative_to(RAIZ))


if __name__ == "__main__":
    main()
