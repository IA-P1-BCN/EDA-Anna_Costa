"""Dashboard interactivo: COVID-19 en Estados Unidos (2020-2021).

Uso, desde la raíz del repositorio y con el entorno activado:

    streamlit run app.py

Si no se ha ejecutado antes el pipeline, la primera carga descarga y prepara los datos.
"""

import plotly.graph_objects as go
import streamlit as st

from src.dashboard import (METRICAS, METRICAS_RANKING, REGIONES_DASHBOARD, cargar_final,
                           estados_de, filtrar, hospitalizados_por_region, marcas_fecha,
                           ranking_100k, resumen, serie_diaria, tabla_datos)
from src.graficos import FONDO, GRIS
from src.informe_calidad import fecha, numero
from src.interactivos import COLORES_REGION, registrar_plantilla
from src.variables import REGIONES

REPOSITORIO = "https://github.com/IA-P1-BCN/EDA-Anna_Costa"
INFORME_CALIDAD = f"{REPOSITORIO}/blob/dev/reports/informe_calidad.md"
CONFIG_GRAFICOS = {"displaylogo": False}
PLANTILLA = "plotly_white+eda"

st.set_page_config(page_title="COVID-19 en EE. UU.", layout="wide")
registrar_plantilla()


@st.cache_data(show_spinner="Preparando los datos (la primera vez tarda unos segundos)...")
def datos():
    """Los datos finales del pipeline, cargados una sola vez por servidor."""
    return cargar_final()


def dibujar(fig: go.Figure, fechas=None) -> None:
    """Muestra un gráfico con la plantilla del proyecto (sin el tema de Streamlit).

    Con `fechas` (el rango elegido), el eje x lleva los meses en castellano.
    """
    # Streamlit pinta su propio fondo si el color solo viene de la plantilla.
    fig.update_layout(template=PLANTILLA, paper_bgcolor=FONDO, plot_bgcolor=FONDO)
    if fechas is not None:
        marcas, etiquetas = marcas_fecha(*fechas)
        fig.update_xaxes(tickvals=marcas, ticktext=etiquetas, hoverformat="%d/%m/%Y")
    st.plotly_chart(fig, theme=None, config=CONFIG_GRAFICOS)


def grafico_evolucion(seleccion, nombre: str) -> go.Figure:
    """Dato diario en gris y media de 7 días con el color de la magnitud."""
    columna, color = METRICAS[nombre]
    serie = serie_diaria(seleccion, columna)
    fig = go.Figure([
        go.Scatter(x=serie.index, y=serie["diaria"], name="Dato diario", mode="lines",
                   line={"color": GRIS, "width": 1},
                   hovertemplate="%{y:,.0f}<extra>Diario</extra>"),
        go.Scatter(x=serie.index, y=serie["media_7d"], name="Media de 7 días", mode="lines",
                   line={"color": color, "width": 2.5},
                   hovertemplate="%{y:,.0f}<extra>Media de 7 días</extra>"),
    ])
    fig.update_layout(title=f"{nombre} al día en la selección", hovermode="x unified",
                      legend={"orientation": "h", "y": 1.08, "x": 0}, height=430)
    fig.update_yaxes(tickformat=",.0f")
    return fig


def grafico_ranking(seleccion, nombre: str) -> go.Figure:
    """Barras horizontales por estado, de mayor a menor tasa, con el color de su región."""
    tabla = ranking_100k(seleccion, METRICAS_RANKING[nombre])
    fig = go.Figure()
    for region in [r for r in REGIONES_DASHBOARD if r in set(tabla["region"])]:
        filas = tabla[tabla["region"] == region]
        fig.add_bar(y=filas["nombre_estado"], x=filas["por_100k"], orientation="h", name=region,
                    marker={"color": COLORES_REGION.get(region, GRIS)},
                    customdata=filas[["total"]],
                    hovertemplate=("<b>%{y}</b><br>%{x:,.0f} por 100.000 hab."
                                   "<br>%{customdata[0]:,.0f} en total<extra></extra>"))
    # Alto según el número de estados; la leyenda va encima de las cifras del eje (arriba).
    alto_barras = max(200, 24 * len(tabla))
    fig.update_layout(title=f"{nombre} por cada 100.000 habitantes en el periodo",
                      height=alto_barras + 160, margin={"t": 130, "b": 30}, barmode="overlay",
                      legend={"orientation": "h", "yanchor": "bottom", "y": 1 + 30 / alto_barras,
                              "x": 0, "title": None})
    fig.update_yaxes(categoryorder="array", categoryarray=tabla["nombre_estado"][::-1],
                     title=None)
    fig.update_xaxes(tickformat=",.0f", side="top")
    return fig


def grafico_hospitalizados(seleccion) -> go.Figure:
    """Una línea por región: hospitalizados por 100.000 habitantes (media de 7 días)."""
    tasa = hospitalizados_por_region(seleccion)
    fig = go.Figure()
    for region in [r for r in REGIONES_DASHBOARD if r in tasa.columns]:
        fig.add_scatter(x=tasa.index, y=tasa[region], name=region, mode="lines",
                        line={"color": COLORES_REGION.get(region, GRIS), "width": 2.5},
                        hovertemplate=f"%{{y:,.1f}}<extra>{region}</extra>")
    fig.update_layout(title="Hospitalizados por cada 100.000 habitantes (media de 7 días)",
                      hovermode="x unified", legend={"orientation": "h", "y": 1.08, "x": 0},
                      height=430)
    return fig


def filtros(final):
    """Panel lateral: devuelve las regiones, los estados y el rango de fechas elegidos."""
    with st.sidebar:
        st.header("Filtros")
        regiones = st.multiselect("Región", REGIONES_DASHBOARD, default=list(REGIONES),
                                  help="Regiones del US Census Bureau. Los territorios van aparte.")
        opciones = estados_de(final, regiones)
        estados = st.multiselect("Estado", list(opciones), format_func=opciones.get,
                                 placeholder="Todos los de las regiones elegidas")
        primero, ultimo = final["fecha"].min().date(), final["fecha"].max().date()
        fechas = st.slider("Fechas", min_value=primero, max_value=ultimo,
                           value=(primero, ultimo), format="DD/MM/YYYY")
        st.divider()
        st.caption(
            "Datos: [The COVID Tracking Project](https://covidtracking.com/data/download) "
            "(CC BY 4.0) y población del US Census Bureau. Cómo se limpiaron: "
            f"[informe de calidad]({INFORME_CALIDAD}). Código: [GitHub]({REPOSITORIO}).")
    return regiones, estados, fechas


def cabecera(seleccion) -> None:
    """Las cuatro cifras principales de la selección."""
    cifras = resumen(seleccion)
    columnas = st.columns(4)
    columnas[0].metric("Casos", numero(cifras["casos"]))
    columnas[1].metric("Muertes", numero(cifras["muertes"]))
    columnas[2].metric("Muertes por 100.000 hab.", numero(cifras["muertes_100k"]),
                       help="Solo estados con población en el censo (sin territorios pequeños).")
    columnas[3].metric("Pico de hospitalizados", numero(cifras["pico_hospitalizados"]),
                       help=f"Personas ingresadas a la vez el {fecha(cifras['fecha_pico'])}.")


def pestanas(seleccion, fechas) -> None:
    """Gráficos y tabla de la selección, cada uno en su pestaña."""
    evolucion, ranking, hospital, datos_tabla = st.tabs(
        ["Evolución", "Ranking por habitante", "Hospitalizados", "Datos"])

    with evolucion:
        metrica = st.radio("Magnitud", list(METRICAS), horizontal=True,
                           label_visibility="collapsed")
        dibujar(grafico_evolucion(seleccion, metrica), fechas)
        st.caption("Los estados publicaban menos los fines de semana: la línea de color (media "
                   "de 7 días) quita ese vaivén y deja ver la tendencia.")

    with ranking:
        metrica = st.radio("Magnitud del ranking", list(METRICAS_RANKING), horizontal=True,
                           label_visibility="collapsed")
        dibujar(grafico_ranking(seleccion, metrica))
        st.caption("Dividir por la población permite comparar estados grandes y pequeños. Los "
                   "territorios sin población en el censo (Guam, Samoa, Marianas e Islas "
                   "Vírgenes) no salen.")

    with hospital:
        dibujar(grafico_hospitalizados(seleccion), fechas)
        st.caption("En marzo y abril de 2020 muchos estados aún no publicaban sus "
                   "hospitalizados: las tasas de esas semanas solo cuentan a los que sí lo hacían.")

    with datos_tabla:
        tabla = tabla_datos(seleccion)
        st.dataframe(tabla, hide_index=True, column_config={
            "Fecha": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Casos nuevos": st.column_config.NumberColumn(format="localized"),
            "Muertes nuevas": st.column_config.NumberColumn(format="localized"),
            "Hospitalizados": st.column_config.NumberColumn(format="localized"),
            "Casos por 100.000 (media 7 días)": st.column_config.NumberColumn(format="%.1f"),
            "Muertes por 100.000 (media 7 días)": st.column_config.NumberColumn(format="%.2f"),
            "Positividad (7 días)": st.column_config.NumberColumn(format="percent"),
        })
        st.download_button("Descargar la selección en CSV",
                           tabla.to_csv(index=False).encode("utf-8"),
                           file_name="covid_seleccion.csv", mime="text/csv")


def main() -> None:
    """La página completa. Streamlit la vuelve a ejecutar cada vez que cambia un filtro."""
    final = datos()
    regiones, estados, fechas = filtros(final)

    st.title("COVID-19 en Estados Unidos, 2020-2021")
    st.caption("Elige regiones, estados y fechas en el panel de la izquierda: todas las cifras y "
               "gráficos se recalculan con tu selección.")

    seleccion = filtrar(final, regiones, estados, *fechas)
    if seleccion.empty:
        st.warning("No hay datos para esta selección. Elige al menos una región.")
        return
    cabecera(seleccion)
    pestanas(seleccion, fechas)


main()
