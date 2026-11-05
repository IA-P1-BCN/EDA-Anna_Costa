"""Genera la presentación del hallazgo principal (5 minutos, público no técnico).

Uso, desde la raíz del repositorio:

    python -m src.presentacion

Escribe reports/presentacion.pdf (diapositivas en 16:9, para proyectar a pantalla completa) y
muestra en la consola cuánto se tarda en contar cada diapositiva, para ensayar con cronómetro.

Todas las cifras se calculan aquí a partir de los datos procesados. Si no existen, se
ejecuta antes el pipeline.
"""

from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

# El backend de matplotlib se elige antes de importar pyplot.
# pylint: disable=wrong-import-position
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from src.dashboard import MESES, cargar_final, hospitalizados_por_region
from src.graficos import (AZUL, FONDO, NARANJA, TEXTO, TEXTO_SUAVE, VERDE, aplicar_estilo,
                          formato_miles, lineas_olas, miles)
from src.informe import NOMBRES_OLA, calcular_cifras, decimal, registrar_fuentes, serie_nacional
from src.interactivos import COLORES_REGION
from src.variables import OLAS, REGIONES

# pylint: enable=wrong-import-position

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "reports"
RUTA_PDF = CARPETA / "presentacion.pdf"

ANCHO, ALTO = 960, 540          # puntos: 16:9
MARGEN = 56
UTIL = ANCHO - 2 * MARGEN       # ancho útil de la diapositiva
PALABRAS_POR_MINUTO = 130       # ritmo tranquilo de una charla
DURACION_MAXIMA = 5             # minutos
AUTORA = "Anna Costa"
EN_PUNTOS = "offset points"     # desplazamiento de las etiquetas de los gráficos

# Ejemplo de la cadena casos -> hospitalizados -> muertes: Florida en la ola de verano.
EJEMPLO = {"estado": "FL", "nombre": "Florida", "desde": "2020-06-01", "hasta": "2020-09-15"}
INDICADORES = {"casos": ("Casos", AZUL), "hospitalizados": ("Hospitalizados", VERDE),
               "muertes": ("Muertes", NARANJA)}

MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------- formato

def dia_mes(dia) -> str:
    """2020-07-16 -> '16 jul' (corto, para los gráficos)."""
    dia = pd.Timestamp(dia)
    return f"{dia.day} {MESES[dia.month - 1]}"


def dia_mes_largo(dia) -> str:
    """2020-07-16 -> '16 de julio' (para el guion, que se lee en voz alta)."""
    dia = pd.Timestamp(dia)
    return f"{dia.day} de {MESES_LARGOS[dia.month - 1]}"


def redondear(numero: float, a: int = 1000) -> str:
    """513972 -> '514.000'."""
    return formato_miles(round(numero / a) * a)


def minutos(texto_: str) -> float:
    """Minutos que se tarda en decir un texto en voz alta, a un ritmo tranquilo."""
    return len(texto_.split()) / PALABRAS_POR_MINUTO


def reloj(minutos_: float) -> str:
    """1.75 -> '1:45'."""
    segundos = round(minutos_ * 60)
    return f"{segundos // 60}:{segundos % 60:02d}"


# ---------------------------------------------------------------- cifras

def cargar_estados() -> pd.DataFrame:
    """Los 50 estados y DC (sin territorios), con la ola como categoría ordenada."""
    final = cargar_final()
    estados = final[~final["es_territorio"].astype(bool)].copy()
    estados["ola"] = pd.Categorical(estados["ola"], categories=list(OLAS), ordered=True)
    return estados


def indicadores(estados: pd.DataFrame, desde="2020-04-01") -> pd.DataFrame:
    """Casos y muertes (media de 7 días) y hospitalizados de cada estado, día a día, desde `desde`.

    Las medias se calculan con toda la serie de cada estado (y al menos 4 días con dato), como en
    el notebook 04, y después se recorta el periodo.
    """
    datos = estados.sort_values(["estado", "fecha"])
    por_estado = datos.groupby("estado")

    def media_7d(columna):
        return por_estado[columna].transform(lambda s: s.rolling(7, min_periods=4).mean())

    tabla = pd.DataFrame({
        "estado": datos["estado"],
        "fecha": datos["fecha"],
        "casos": media_7d("casos_nuevos"),
        "hospitalizados": datos["hospitalizados_actuales"],
        "muertes": media_7d("muertes_nuevas"),
    })
    return tabla[tabla["fecha"] >= pd.Timestamp(desde)]


def mejor_desfase(datos: pd.DataFrame, origen: str, destino: str,
                  maximo: int = 35) -> tuple[int, float]:
    """Días que hay que adelantar `origen` para que encaje mejor con `destino`.

    Para cada desfase k se calcula, en cada estado, la correlación entre `origen` de hace k días
    y `destino` de hoy; se toma la mediana de los estados y se devuelve el k con la mediana más
    alta (con esa correlación). Es el mismo cálculo del notebook 04.
    """
    grupos = [grupo for _, grupo in datos.groupby("estado")]
    curva = pd.Series({
        k: np.nanmedian([g[origen].shift(k).corr(g[destino]) for g in grupos])
        for k in range(maximo + 1)
    })
    return int(curva.idxmax()), float(curva.max())


def serie_estado(estados: pd.DataFrame, estado: str, desde, hasta) -> pd.DataFrame:
    """Casos, hospitalizados y muertes de un estado entre dos fechas."""
    datos = indicadores(estados[estados["estado"] == estado], desde="2020-01-01")
    return datos.set_index("fecha").loc[desde:hasta, list(INDICADORES)]


def picos(serie: pd.DataFrame) -> dict[str, pd.Timestamp]:
    """Fecha del máximo de cada columna."""
    return {columna: serie[columna].idxmax() for columna in serie}


def calcular(estados: pd.DataFrame) -> dict:
    """Todas las cifras de la presentación."""
    nacional = serie_nacional(estados)
    cifras = calcular_cifras(estados, nacional)
    datos = indicadores(estados)
    cifras["desfase_hosp"] = mejor_desfase(datos, "casos", "hospitalizados")
    cifras["desfase_muertes"] = mejor_desfase(datos, "hospitalizados", "muertes")
    cifras["desfase_casos_muertes"] = mejor_desfase(datos, "casos", "muertes")

    ejemplo = serie_estado(estados, EJEMPLO["estado"], EJEMPLO["desde"], EJEMPLO["hasta"])
    cifras["ejemplo"] = ejemplo
    cifras["picos_ejemplo"] = picos(ejemplo)

    regiones = hospitalizados_por_region(estados[estados["fecha"] >= "2020-10-01"])
    cifras["hosp_regiones"] = regiones
    cifras["picos_regiones"] = regiones.idxmax()
    cifras["ceros_sin_publicar"] = int(estados["cero_sin_publicar"].astype(bool).sum())
    cifras["nacional"] = nacional
    return cifras


# ---------------------------------------------------------------- guion

def guiones(cifras: dict) -> list[str]:
    """Lo que se dice en cada diapositiva, en el mismo orden que las diapositivas."""
    por_ola = cifras["por_ola"]
    fl = {columna: dia_mes_largo(dia) for columna, dia in cifras["picos_ejemplo"].items()}
    dias_fl = (cifras["picos_ejemplo"]["muertes"] - cifras["picos_ejemplo"]["hospitalizados"]).days
    regiones = cifras["picos_regiones"]
    primera = regiones.idxmin()
    resto = regiones.drop(primera)
    semanas = round((resto.min() - regiones[primera]).days / 7)
    pico_diario = formato_miles(por_ola["pico_muertes"].max() // 100 * 100)
    return [
        "Buenos días. Os voy a contar catorce meses de pandemia en Estados Unidos y una lección "
        "que sale de los datos: cuando los hospitales empiezan a llenarse, todavía quedan unas dos "
        "semanas para actuar antes de que lleguen las muertes.",

        "Entre enero de 2020 y marzo de 2021 se notificaron casi "
        f"{round(cifras['total_casos'] / 1e6)} millones de casos y unas "
        f"{redondear(cifras['total_muertes'])} muertes. En el peor momento, en enero de 2021, "
        f"morían más de {pico_diario} personas al día.",

        "La pandemia llegó en tres olas: la primavera de 2020, el verano y el otoño-invierno. La "
        f"última fue, con diferencia, la peor: dejó unas {redondear(por_ola['muertes'].iloc[2])} "
        "muertes, más que las dos anteriores juntas.",

        "Ante cifras así, la pregunta de cualquier directivo es: ¿se podía ver venir? Analizando "
        "los cincuenta estados día a día, la respuesta es que sí. Y el aviso no venía de donde "
        "solemos mirar, los casos, sino de los hospitales.",

        "Esto es lo que encontramos. Cuando suben los casos en un estado, los ingresos en el "
        f"hospital suben unos {cifras['desfase_hosp'][0]} días después. Y las muertes llegan unos "
        f"{cifras['desfase_muertes'][0]} días después de los ingresos. Es decir: los "
        "hospitalizados de hoy anuncian las muertes de dentro de casi dos semanas.",

        f"Un ejemplo: {EJEMPLO['nombre']} en el verano de 2020. Los casos tocaron techo el "
        f"{fl['casos']} y los hospitalizados el {fl['hospitalizados']}. Las muertes no llegaron a "
        f"su máximo hasta el {fl['muertes']}, {dias_fl} días después que los hospitales. Ese es "
        "el margen para preparar camas, personal y material.",

        "¿Por qué fijarse en los hospitales y no en los casos? Porque los casos engañan. Dependen "
        "de cuántas pruebas se hagan: al principio solo se analizaba a quien tenía síntomas "
        "claros. Y tienen calendario: muchos estados no publicaban en fin de semana. Una persona "
        "ingresada, en cambio, cuenta igual cualquier día.",

        "Y hay un matiz importante: cada región tiene su propio calendario. En la ola de invierno, "
        f"los hospitales del {primera} llegaron a su máximo el {dia_mes_largo(regiones[primera])}; "
        f"los del resto del país, entre el {resto.min().day} y el {dia_mes_largo(resto.max())}, "
        f"unas {semanas} semanas después. La media nacional habría escondido ese aviso.",

        "Por eso propongo tres cosas. Primera: vigilar cada día los ingresos hospitalarios, región "
        "por región, como señal de alarma principal. Segunda: cuando suban, activar el plan para "
        "las dos semanas siguientes, con camas, personal y material. Y tercera: reforzar primero "
        "donde empieza la ola y mover recursos hacia las regiones que vienen detrás.",

        "Me quedo con una frase: cuando los hospitales se llenan, quedan unas dos semanas para "
        "actuar. Los datos estaban ahí; la clave es mirarlos a tiempo. Muchas gracias.",
    ]


# ---------------------------------------------------------------- gráficos

def estilo_diapositiva() -> None:
    """El estilo del proyecto con letra más grande, para que se lea proyectado."""
    aplicar_estilo()
    plt.rcParams.update({"font.size": 15, "axes.titlesize": 17, "axes.labelsize": 15,
                         "xtick.labelsize": 14, "ytick.labelsize": 14, "legend.fontsize": 14,
                         "lines.linewidth": 2.5})


def eje_meses(ax, corto: bool = False) -> None:
    """Meses en castellano en el eje x: 'abr 20' cada dos meses, o 'abr' cada mes si `corto`."""
    def formato(valor, _):
        dia = mdates.num2date(valor)
        return MESES[dia.month - 1] if corto else f"{MESES[dia.month - 1]} {dia:%y}"
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1 if corto else 2))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(formato))
    ax.grid(axis="x", visible=False)


def a_imagen(fig) -> ImageReader:
    """Figura de matplotlib como imagen para reportlab (sin pasar por disco)."""
    fig.tight_layout()
    memoria = BytesIO()
    fig.savefig(memoria, format="png", dpi=200, facecolor=FONDO)
    plt.close(fig)
    memoria.seek(0)
    return ImageReader(memoria)


def punto(ax, x, y, color: str) -> None:
    """Marca un máximo con un punto rodeado del color del fondo."""
    ax.scatter(x, y, s=90, color=color, edgecolors=FONDO, linewidths=2, zorder=3)


def grafico_olas(cifras: dict, medidas) -> ImageReader:
    """Muertes al día (media de 7 días) con las tres olas y el pico de cada una."""
    serie = cifras["nacional"].loc["2020-03-01":, "muertes"]
    cortes = pd.to_datetime(list(OLAS.values()))[:2]
    fig, ax = plt.subplots(figsize=medidas)
    ax.fill_between(serie.index, serie, color=NARANJA, alpha=0.15, linewidth=0)
    ax.plot(serie.index, serie, color=NARANJA)
    lineas_olas(ax, cortes)
    inicios = [serie.index[0], *(cortes + pd.Timedelta(days=1))]
    finales = [*cortes, serie.index[-1]]
    for nombre, inicio, fin in zip(NOMBRES_OLA, inicios, finales):
        tramo = serie.loc[inicio:fin]
        punto(ax, tramo.idxmax(), tramo.max(), NARANJA)
        ax.annotate(f"{formato_miles(tramo.max())} al día", xy=(tramo.idxmax(), tramo.max()),
                    xytext=(0, 10), textcoords=EN_PUNTOS, ha="center", color=TEXTO,
                    fontsize=15, fontweight="bold")
        ax.text(inicio + (fin - inicio) / 2, serie.max() * 1.22, nombre, ha="center",
                color=TEXTO_SUAVE, fontsize=14)
    ax.set_ylim(0, serie.max() * 1.3)
    ax.yaxis.set_major_formatter(miles)
    ax.set_ylabel("Muertes al día (media de 7 días)")
    eje_meses(ax)
    return a_imagen(fig)


def grafico_ejemplo(cifras: dict, medidas) -> ImageReader:
    """Casos, hospitalizados y muertes de un estado como % de su máximo, con cada pico."""
    serie = cifras["ejemplo"]
    indice = serie / serie.max() * 100
    # Las etiquetas de los picos van escalonadas para que no se pisen (casos e ingresos van muy
    # juntos): altura, alineación y desplazamiento en puntos.
    colocacion = {"casos": (119, "right", -6), "hospitalizados": (109, "left", 6),
                  "muertes": (119, "left", 6)}
    fig, ax = plt.subplots(figsize=medidas)
    for columna, (nombre, color) in INDICADORES.items():
        pico = cifras["picos_ejemplo"][columna]
        altura, alineacion, desplazamiento = colocacion[columna]
        ax.plot(indice.index, indice[columna], color=color, label=nombre)
        punto(ax, pico, 100, color)
        ax.axvline(pico, ymax=100 / 127, color=color, linewidth=1, linestyle=":")
        ax.annotate(f"{nombre}: {dia_mes(pico)}", xy=(pico, altura), xytext=(desplazamiento, 0),
                    textcoords=EN_PUNTOS, ha=alineacion, va="center", color=TEXTO,
                    fontsize=14, fontweight="bold" if columna == "muertes" else "normal")
    ax.set_ylim(0, 127)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("% del máximo del verano")
    ax.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.32))
    eje_meses(ax, corto=True)
    return a_imagen(fig)


def grafico_regiones(cifras: dict, medidas) -> ImageReader:
    """Hospitalizados por 100.000 habitantes de cada región en la ola de invierno."""
    tasa = cifras["hosp_regiones"]
    fig, ax = plt.subplots(figsize=medidas)
    for region in REGIONES:
        ax.plot(tasa.index, tasa[region], color=COLORES_REGION[region], label=region)
        punto(ax, tasa[region].idxmax(), tasa[region].max(), COLORES_REGION[region])
    primera = cifras["picos_regiones"].idxmin()
    pico = cifras["picos_regiones"][primera]
    ax.annotate(f"{primera}: máximo el {dia_mes(pico)}", xy=(pico, tasa[primera].max()),
                xytext=(0, 16), textcoords=EN_PUNTOS, ha="center", color=TEXTO,
                fontsize=14, fontweight="bold")
    resto = cifras["picos_regiones"].drop(primera)
    ax.annotate(f"Resto: del {resto.min().day} al {dia_mes(resto.max())}",
                xy=(resto.min(), tasa.max().max()), xytext=(0, 18), textcoords=EN_PUNTOS,
                ha="center", color=TEXTO, fontsize=14)
    ax.set_ylim(0, tasa.max().max() * 1.25)
    ax.set_ylabel("Hospitalizados por 100.000 hab.")
    ax.legend(loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.32))
    eje_meses(ax, corto=True)
    return a_imagen(fig)


# ---------------------------------------------------------------- piezas de las diapositivas

def estilo(nombre: str, tamano: float, negrita: bool = False, **opciones) -> ParagraphStyle:
    """Estilo de párrafo con la fuente del proyecto (interlineado 1,25 por defecto)."""
    opciones.setdefault("leading", tamano * 1.25)
    opciones.setdefault("textColor", colors.HexColor(TEXTO))
    return ParagraphStyle(nombre, fontName="DejaVu-Bold" if negrita else "DejaVu",
                          fontSize=tamano, **opciones)


def estilos() -> dict:
    """Estilos de texto de las diapositivas."""
    gris = colors.HexColor(TEXTO_SUAVE)
    return {
        "titulo": estilo("titulo", 30, True, leading=36),
        "portada": estilo("portada", 54, True, leading=62),
        "grande": estilo("grande", 40, True, alignment=TA_CENTER),
        "subtitulo": estilo("subtitulo", 20, leading=28, textColor=gris),
        "cuerpo": estilo("cuerpo", 20, leading=28),
        "centro": estilo("centro", 24, leading=34, alignment=TA_CENTER),
        "cifra": estilo("cifra", 46, True, leading=54, alignment=TA_CENTER),
        "etiqueta": estilo("etiqueta", 18, leading=24, textColor=gris, alignment=TA_CENTER),
        "flecha": estilo("flecha", 21, True, alignment=TA_CENTER),
        "caja": estilo("caja", 24, True, alignment=TA_CENTER),
        "tarjeta_titulo": estilo("tarjeta_titulo", 21, True, leading=27),
        "tarjeta": estilo("tarjeta", 17, leading=24),
        "nota": estilo("nota", 12, leading=16, textColor=gris),
    }


def texto(c: Canvas, contenido: str, estilo_, donde: tuple[float, float, float]) -> float:
    """Escribe un párrafo en `donde` = (x, borde superior, ancho); devuelve su borde inferior."""
    x, arriba, ancho = donde
    parrafo = Paragraph(contenido, estilo_)
    _, alto = parrafo.wrap(ancho, ALTO)
    parrafo.drawOn(c, x, arriba - alto)
    return arriba - alto


def titulo(c: Canvas, e: dict, contenido: str) -> float:
    """Título de la diapositiva arriba a la izquierda; devuelve su borde inferior."""
    return texto(c, contenido, e["titulo"], (MARGEN, ALTO - 48, UTIL))


def nota(c: Canvas, e: dict, contenido: str, arriba: float = 70) -> None:
    """Texto pequeño al pie (fuente o aclaración)."""
    texto(c, contenido, e["nota"], (MARGEN, arriba, UTIL))


def grafico(c: Canvas, e: dict, contenido: str, dibujar, cifras: dict) -> None:
    """Diapositiva con título y un gráfico que ocupa el resto."""
    arriba = titulo(c, e, contenido) - 16
    medidas = (UTIL / 72, (arriba - 40) / 72)      # pulgadas
    c.drawImage(dibujar(cifras, medidas), MARGEN, 40, width=UTIL, height=arriba - 40)


def caja(c: Canvas, rect: tuple[float, float, float, float], relleno: str,
         borde: str | None = None) -> None:
    """Rectángulo redondeado en `rect` = (x, y, ancho, alto)."""
    c.setFillColor(colors.HexColor(relleno))
    c.setStrokeColor(colors.HexColor(borde or relleno))
    c.setLineWidth(2)
    c.roundRect(*rect, 10, fill=1, stroke=1 if borde else 0)


def suave(color: str, cantidad: float = 0.9) -> str:
    """Mezcla un color con el fondo (para rellenos claros)."""
    base, fondo = colors.HexColor(color), colors.HexColor(FONDO)
    mezcla = [a * (1 - cantidad) + b * cantidad for a, b in
              zip((base.red, base.green, base.blue), (fondo.red, fondo.green, fondo.blue))]
    return colors.Color(*mezcla).hexval().replace("0x", "#")


def tarjetas(c: Canvas, contenidos: list, rect_y: tuple[float, float], dibujar) -> None:
    """Tres tarjetas en fila con una franja de color arriba.

    `contenidos` es una lista de (color, datos); `rect_y` = (y inferior, alto); `dibujar(x, ancho,
    datos)` escribe el contenido de cada tarjeta.
    """
    hueco = 28
    ancho = (UTIL - 2 * hueco) / 3
    abajo, alto = rect_y
    for i, (color, datos) in enumerate(contenidos):
        x = MARGEN + i * (ancho + hueco)
        caja(c, (x, abajo, ancho, alto), suave(color))
        c.setFillColor(colors.HexColor(color))
        c.rect(x, abajo + alto - 6, ancho, 6, fill=1, stroke=0)
        dibujar(x, ancho, datos)


def flecha(c: Canvas, x0: float, x1: float, y: float) -> None:
    """Flecha horizontal de x0 a x1."""
    c.setStrokeColor(colors.HexColor(TEXTO_SUAVE))
    c.setFillColor(colors.HexColor(TEXTO_SUAVE))
    c.setLineWidth(3)
    c.line(x0, y, x1 - 12, y)
    camino = c.beginPath()
    camino.moveTo(x1, y)
    camino.lineTo(x1 - 16, y + 9)
    camino.lineTo(x1 - 16, y - 9)
    camino.close()
    c.drawPath(camino, fill=1, stroke=0)


def franja_lateral(c: Canvas) -> None:
    """Franja verde a la izquierda de la portada y del cierre."""
    caja(c, (0, 0, 14, ALTO), VERDE)


# ---------------------------------------------------------------- diapositivas

def d_portada(c: Canvas, e: dict, _cifras: dict) -> None:
    """1. Título del hallazgo."""
    franja_lateral(c)
    x = MARGEN + 10
    fin = texto(c, "Dos semanas de ventaja", e["portada"], (x, ALTO - 150, UTIL))
    texto(c, "Qué nos enseñan los datos de la COVID-19 en Estados Unidos para adelantarnos a la "
             "próxima crisis sanitaria", e["subtitulo"], (x, fin - 20, 640))
    texto(c, AUTORA, e["cuerpo"], (x, 130, 600))
    texto(c, "Datos de The COVID Tracking Project · enero de 2020 a marzo de 2021 · 50 estados y "
             "Washington D. C.", e["nota"], (x, 98, 800))


def d_cifras(c: Canvas, e: dict, cifras: dict) -> None:
    """2. Las tres cifras que dan la dimensión."""
    titulo(c, e, "Catorce meses que cambiaron el país")
    pico = cifras["fecha_pico_muertes"]
    contenidos = [
        (AZUL, (decimal(cifras["total_casos"] / 1e6), "millones de casos notificados")),
        (NARANJA, (redondear(cifras["total_muertes"]), "muertes")),
        (NARANJA, (formato_miles(cifras["por_ola"]["pico_muertes"].max()),
                   f"muertes al día en el peor momento ({MESES_LARGOS[pico.month - 1]} de "
                   f"{pico.year})")),
    ]

    def escribir(x, ancho, datos):
        fin = texto(c, datos[0], e["cifra"], (x + 10, 320, ancho - 20))
        texto(c, datos[1], e["etiqueta"], (x + 20, fin - 14, ancho - 40))

    tarjetas(c, contenidos, (130, 250), escribir)
    nota(c, e, "Cifras de los 50 estados y Washington D. C. entre el 13 de enero de 2020 y el 7 de "
               "marzo de 2021.", arriba=100)


def d_olas(c: Canvas, e: dict, cifras: dict) -> None:
    """3. Las tres olas."""
    grafico(c, e, "No fue una ola, sino tres, y la peor llegó en invierno", grafico_olas, cifras)


def d_pregunta(c: Canvas, e: dict, _cifras: dict) -> None:
    """4. La pregunta y la respuesta corta."""
    texto(c, "¿Se podía ver venir?", e["grande"], (MARGEN, 380, UTIL))
    caja(c, (150, 150, ANCHO - 300, 140), suave(VERDE, 0.88))
    texto(c, "Sí. <b>Los hospitales avisaban unas dos semanas antes</b> de que subieran las "
             "muertes.", e["centro"], (180, 258, ANCHO - 360))


def d_cadena(c: Canvas, e: dict, cifras: dict) -> None:
    """5. El hallazgo: casos -> hospitalizados -> muertes, con los días de retraso."""
    fin = titulo(c, e, "Primero suben los casos, luego los hospitales y después las muertes")
    ancho, alto = 200, 120
    hueco = (UTIL - 3 * ancho) / 2
    y = fin - 90 - alto
    for i, (nombre, color) in enumerate(INDICADORES.values()):
        x = MARGEN + i * (ancho + hueco)
        caja(c, (x, y, ancho, alto), suave(color, 0.85), color)
        texto(c, nombre, e["caja"], (x, y + alto / 2 + 15, ancho))
        if i < 2:
            dias = [cifras["desfase_hosp"], cifras["desfase_muertes"]][i][0]
            flecha(c, x + ancho + 14, x + ancho + hueco - 14, y + alto / 2)
            texto(c, f"+{dias} días", e["flecha"], (x + ancho, y + alto / 2 + 40, hueco))
    texto(c, "Los hospitalizados de hoy anuncian las muertes de <b>dentro de casi dos "
             "semanas</b>.", e["centro"], (MARGEN + 40, y - 50, UTIL - 80))
    nota(c, e, "Retraso con el que cada indicador encaja mejor con el anterior: mediana de los 51 "
               "estados, de abril de 2020 a marzo de 2021. Casos y muertes en media de 7 días.")


def d_ejemplo(c: Canvas, e: dict, cifras: dict) -> None:
    """6. Un caso concreto: Florida en el verano de 2020."""
    picos_ = cifras["picos_ejemplo"]
    dias = (picos_["muertes"] - picos_["hospitalizados"]).days
    grafico(c, e, f"En {EJEMPLO['nombre']}, las muertes tocaron techo {dias} días después que "
                  "los hospitales", grafico_ejemplo, cifras)


def d_por_que(c: Canvas, e: dict, cifras: dict) -> None:
    """7. Por qué mirar los hospitalizados y no los casos."""
    fin = titulo(c, e, "¿Por qué los hospitales y no los casos?")
    uno_de_cada = round(100 / cifras["por_ola"]["pico_positividad"].iloc[0])
    ceros = formato_miles(cifras["ceros_sin_publicar"])
    contenidos = [
        (AZUL, ("Los casos dependen de las pruebas",
                f"En la primavera de 2020 salía positiva <b>1 de cada {uno_de_cada}</b> pruebas: "
                "solo se analizaba a quien tenía síntomas claros.")),
        (AZUL, ("Los casos tienen calendario",
                f"Muchos estados no publicaban en fin de semana: <b>{ceros} días</b> aparecen con "
                "0 casos sin serlo.")),
        (VERDE, ("Los ingresos no se toman días libres",
                 "Una persona hospitalizada cuenta igual cualquier día, y los ingresos encajan "
                 "mejor con las muertes que vienen después.")),
    ]

    def escribir(x, ancho, datos):
        abajo = texto(c, datos[0], e["tarjeta_titulo"], (x + 20, fin - 70, ancho - 40))
        texto(c, datos[1], e["tarjeta"], (x + 20, abajo - 16, ancho - 40))

    tarjetas(c, contenidos, (90, fin - 130), escribir)
    hosp, casos = cifras["desfase_muertes"][1], cifras["desfase_casos_muertes"][1]
    nota(c, e, "Parecido con las muertes de días después (correlación, mediana de los estados; "
               f"1 = idénticas): hospitalizados {decimal(hosp, 2)}, casos {decimal(casos, 2)}.")


def d_regiones(c: Canvas, e: dict, cifras: dict) -> None:
    """8. Cada región tuvo su calendario."""
    grafico(c, e, "El aviso no llega a la vez a todo el país", grafico_regiones, cifras)


def d_propuesta(c: Canvas, e: dict, _cifras: dict) -> None:
    """9. Las tres recomendaciones."""
    arriba = titulo(c, e, "Qué propongo") - 40
    pasos = [
        ("Vigilar", "los ingresos hospitalarios cada día, región por región, como señal de alarma "
                    "principal."),
        ("Activar", "el plan en cuanto suban: camas de UCI, personal y material para las dos "
                    "semanas siguientes."),
        ("Reforzar", "primero donde empieza la ola y mover recursos hacia las regiones que vienen "
                     "detrás."),
    ]
    for numero, (verbo, resto) in enumerate(pasos, start=1):
        caja(c, (MARGEN, arriba - 70, 70, 70), VERDE)
        c.setFillColor(colors.white)
        c.setFont("DejaVu-Bold", 34)
        c.drawCentredString(MARGEN + 35, arriba - 47, str(numero))
        texto(c, f"<b>{verbo}</b> {resto}", e["cuerpo"], (MARGEN + 100, arriba - 8, UTIL - 100))
        arriba -= 110


def d_cierre(c: Canvas, e: dict, _cifras: dict) -> None:
    """10. La frase para recordar, los límites y la fuente."""
    franja_lateral(c)
    fin = texto(c, "Cuando los hospitales se llenan, quedan unas dos semanas para actuar.",
                e["grande"], (120, 420, ANCHO - 240))
    texto(c, "Los datos estaban ahí: la clave es mirarlos a tiempo.", e["centro"],
          (120, fin - 28, ANCHO - 240))
    texto(c, "Límites: los datos acaban el 7 de marzo de 2021, cada estado contaba a su manera y "
             "los casos de la primavera de 2020 están por debajo de los reales. Las conclusiones "
             "se apoyan en tendencias, no en cifras exactas.<br/>Fuente: The COVID Tracking "
             "Project (The Atlantic), CC BY 4.0, y censo de EE. UU. Análisis completo: "
             "github.com/IA-P1-BCN/EDA-Anna_Costa", e["nota"], (MARGEN + 10, 110, UTIL - 10))


DIAPOSITIVAS = [
    ("Portada", d_portada),
    ("Las cifras", d_cifras),
    ("Tres olas", d_olas),
    ("La pregunta", d_pregunta),
    ("El hallazgo", d_cadena),
    ("Un ejemplo", d_ejemplo),
    ("Por qué los hospitales", d_por_que),
    ("Cada región a su ritmo", d_regiones),
    ("Propuesta", d_propuesta),
    ("Cierre", d_cierre),
]


# ---------------------------------------------------------------- salida

def construir_pdf(cifras: dict, ruta: Path = RUTA_PDF) -> None:
    """Dibuja todas las diapositivas en un PDF de 16:9."""
    registrar_fuentes()
    estilo_diapositiva()
    e = estilos()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(ruta), pagesize=(ANCHO, ALTO))
    c.setTitle("Dos semanas de ventaja: COVID-19 en Estados Unidos")
    c.setAuthor(AUTORA)
    for numero, (_, dibujar) in enumerate(DIAPOSITIVAS, start=1):
        c.setFillColor(colors.HexColor(FONDO))
        c.rect(0, 0, ANCHO, ALTO, fill=1, stroke=0)
        dibujar(c, e, cifras)
        if 1 < numero < len(DIAPOSITIVAS):
            c.setFont("DejaVu", 11)
            c.setFillColor(colors.HexColor(TEXTO_SUAVE))
            c.drawRightString(ANCHO - MARGEN, 24, f"{numero} / {len(DIAPOSITIVAS)}")
        c.showPage()
    c.save()


def tiempos(textos: list[str]) -> list[tuple[int, str, str, str]]:
    """Una fila por diapositiva: número, nombre, tiempo y tiempo acumulado al acabarla."""
    filas, acumulado = [], 0.0
    for numero, ((nombre, _), guion) in enumerate(zip(DIAPOSITIVAS, textos), start=1):
        acumulado += minutos(guion)
        filas.append((numero, nombre, reloj(minutos(guion)), reloj(acumulado)))
    return filas


def generar(ruta_pdf: Path = RUTA_PDF) -> list[str]:
    """Escribe las diapositivas; devuelve lo que se dice en cada una."""
    cifras = calcular(cargar_estados())
    construir_pdf(cifras, ruta_pdf)
    return guiones(cifras)


def main() -> None:
    """`python -m src.presentacion`: genera las diapositivas y muestra los tiempos para ensayar."""
    textos = generar()
    print(f"Presentación guardada en {RUTA_PDF.relative_to(RAIZ)}.")
    print(f"Duración estimada a {PALABRAS_POR_MINUTO} palabras por minuto (máximo: "
          f"{DURACION_MAXIMA} minutos):")
    for numero, nombre, tiempo, acumulado in tiempos(textos):
        print(f"  {numero:>2}. {nombre:<24} {tiempo}  (al acabar: {acumulado})")


if __name__ == "__main__":
    main()
