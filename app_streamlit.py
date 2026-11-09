"""App Streamlit para dashboard COVID-19 en Estados Unidos (2020-2021).

Versión optimizada para despliegue en Streamlit Cloud.
Carga datos directamente desde CSVs locales sin necesidad del pipeline completo.
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================

st.set_page_config(
    page_title="COVID-19 Dashboard EE.UU.",
    layout="wide",
    page_icon="🦠"
)

st.title("📊 COVID-19 en Estados Unidos (2020-2021)")
st.markdown("""
Este dashboard interactivo muestra los datos de COVID-19 procesados desde The COVID Tracking Project.

**Fuentes de datos:**
- [The COVID Tracking Project](https://covidtracking.com/data/download) - CC BY 4.0
- US Census Bureau (población por estado)
""")

# ============================================
# CARGA DE DATOS
# ============================================

@st.cache_data
def cargar_datos_crudos():
    """Carga los datos crudos desde data/raw/"""
    try:
        ruta_raw = Path("data/raw/covid_states_daily.csv")
        if not ruta_raw.exists():
            st.error(f"❌ No se encontró el archivo en: {ruta_raw}")
            return None
        
        df = pd.read_csv(ruta_raw)
        print(f"✅ Cargado {len(df)} registros desde {ruta_raw}")
        
        # Mostrar columnas principales
        print(f"\n📊 Columnas ({len(df.columns)}):")
        for col in df.columns[:15]:  # Solo mostrar primeras 15 columnas
            print(f"  - {col}")
        
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return None

# ============================================
# PREPROCESAMIENTO DE DATOS (Simplificado)
# ============================================

@st.cache_data
def preparar_datos(df_cruo):
    """Prepara los datos para visualización."""
    try:
        # Verificar columnas esenciales
        columnas_esenciales = ["fecha", "estado", "casos", "muertes", "hospitalizados"]
        
        df = df_cruo.copy()
        
        # Asegurar tipos de datos correctos
        df["fecha"] = pd.to_datetime(df["fecha"], errors='coerce')
        df["estado"] = df["estado"].astype(str)
        
        # Filtrar fechas inválidas
        df = df[df["fecha"].notna()]
        
        print(f"✅ Datos preparados: {len(df)} registros válidos")
        return df
        
    except Exception as e:
        st.error(f"❌ Error en preprocesamiento: {e}")
        return None

@st.cache_data
def agregar_poblacion(df_datos, nombre_archivo_poblacion=None):
    """Agrega datos de población del Census (si están disponibles)."""
    try:
        if nombre_archivo_poblacion is None:
            nombre_archivo_poblacion = "data/raw/poblacion_estados_census.csv"
        
        ruta_censo = Path(nombre_archivo_poblacion)
        if not ruta_censo.exists():
            return df_datos  # Retornar sin datos de población
        
        censo_df = pd.read_csv(ruta_censo)
        
        # Unir con los datos COVID
        columnas_comunes = ["estado"]
        
        # Ajustar nombres según el dataset del Census
        for col in censo_df.columns:
            if "NAME" in str(col).upper():
                df_datos["poblacion"] = censo_df[col]
                print(f"✅ Población agregada desde columna: {col}")
                break
        
        return df_datos
    except Exception as e:
        print(f"⚠️ No se pudo cargar población (no crítico): {e}")
        return df_datos

# ============================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================

def grafico_evolution(df, metrica, fecha_inicio=None, fecha_fin=None):
    """Gráfico de evolución temporal con Plotly."""
    if metrica not in ["casos", "muertes", "hospitalizados"]:
        metrica = "casos"
    
    # Filtrar por rango de fechas si se especifica
    df_filtrado = df.copy()
    if fecha_inicio and fecha_fin:
        df_filtrado = df_filtrated[
            (df_filtrado["fecha"] >= fecha_inicio) & 
            (df_filtrado["fecha"] <= fecha_fin)
        ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_filtrado["fecha"],
        y=df_filtrado[metrica],
        mode='lines+markers',
        name=metrica.capitalize(),
        line=dict(color='#2a78d6', width=2, dash='solid')
    ))
    
    fig.update_layout(
        title=f"Evolución de {metrica.upper()} en EE.UU. (2020-2021)",
        xaxis_title="Fecha",
        yaxis_title=metrica.capitalize(),
        hovermode='x unified',
        template='plotly_white',
        height=450
    )
    
    return fig

def grafico_ranking(df, metrica):
    """Ranking por estado con barras horizontales."""
    if metrica not in ["casos", "muertes"]:
        metrica = "casos"
    
    # Agrupar y ordenar
    ranking = df.groupby("estado")[metrica].sum().nlargest(10)
    ranking_df = pd.DataFrame({
        'estado': ranking.index, 
        'valor': ranking.values
    })
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ranking_df['estado'],
        y=ranking_df['valor'],
        name=f'Top 10 {metrica.upper()}',
        marker_color='#2a78d6',
        orientation='h'
    ))
    
    fig.update_layout(
        title=f"Top 10 Estados por {metrica.upper()}",
        yaxis={'categoryorder': 'total ascending'},
        template='plotly_white',
        height=350
    )
    
    return fig

def grafico_hospitalizados(df):
    """Gráfico de hospitalizados por región."""
    # Agrupar por región (si la columna existe)
    if "region" in df.columns:
        regional = df.groupby("region")["hospitalizados"].mean().nlargest(8)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=regional.index,
            y=regional.values,
            name='Hospitalizados (promedio)',
            marker_color='#4a9c26',
            orientation='h'
        ))
        
        fig.update_layout(
            title="Hospitalizados Promedio por Región",
            template='plotly_white',
            height=350
        )
        return fig
    
    # Si no hay región, mostrar top 10 estados
    top_estados = df.groupby("estado")["hospitalizados"].mean().nlargest(10)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_estados.index,
        y=top_estados.values,
        marker_color='#4a9c26',
        orientation='h'
    ))
    
    fig.update_layout(
        title="Hospitalizados Promedio por Estado",
        template='plotly_white',
        height=350
    )
    
    return fig

# ============================================
# PANEL LATERAL (Filtros)
# ============================================

def panel_lateral(df_datos):
    """Configura el panel lateral con filtros."""
    with st.sidebar:
        st.header("🎛️ Filtros")
        
        # Selector de métrica principal
        metrica = st.selectbox(
            "Seleccionar métrica:",
            ["casos", "muertes", "hospitalizados"],
            help="Elige qué variable visualizar"
        )
        
        st.divider()
        
        # Rango temporal
        if "fecha" in df_datos.columns:
            fecha_fin = st.date_input(
                "Fecha final:", 
                value=pd.to_datetime(df_datos["fecha"]).max(),
                max_value=pd.to_datetime(df_datos["fecha"]).max()
            )
            fecha_inicio = st.date_input(
                "Fecha inicial:", 
                value=fecha_fin.replace(year=fecha_fin.year - 1),
                min_value=pd.to_datetime(df_datos["fecha"]).min(),
                max_value=fecha_fin
            )
        else:
            st.info("📅 Sin datos temporales disponibles")
        
        st.divider()
        
        # Información de datos
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.metric("Total Registros", len(df_datos))
        with info_col2:
            estados_unicos = df_datos["estado"].nunique()
            st.metric("Estados con Datos", estados_unicos)
        
        st.divider()
        
        st.info("""
        📚 **Información**
        - Fuente: The COVID Tracking Project
        
        🔗 [Ver código en GitHub](https://github.com/IA-P1-BCN/EDA-Anna_Costa)
        
        🌐 Datos CC BY 4.0
        """)

# ============================================
# PÁGINA PRINCIPAL
# ============================================

def main():
    """Renderiza el dashboard completo."""
    
    # Cargar datos crudos (se hace una vez gracias a @st.cache_data)
    df_cruo = cargar_datos_crudos()
    
    if df_cruo is None:
        st.error("⚠️ No se pudieron cargar los datos. Verifica que `data/raw/covid_states_daily.csv` esté en el repositorio.")
        st.stop()
    
    # Preparar datos
    df_preparado = preparar_datos(df_cruo)
    df_con_poblacion = agregar_poblacion(df_preparado)
    
    if df_preparado is None:
        st.error("⚠️ No se pudieron preparar los datos.")
        st.stop()
    
    # Panel lateral con filtros
    panel_lateral(df_con_poblacion)
    
    # Cabecera con métricas clave
    st.header("📊 Métricas Clave")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_casos = df_con_poblacion["casos"].sum()
        st.metric(label="Casos Totales", value=f"{total_casos:,}", delta="")
    
    with col2:
        total_muertes = df_con_poblacion["muertes"].sum()
        st.metric(label="Muertes Totales", value=total_muertes, delta="")
    
    with col3:
        # Pico de hospitalizados (si existe)
        if "hospitalizados" in df_con_poblacion.columns:
            pico = df_con_poblacion["hospitalizados"].max()
            st.metric(label="Pico Hospitalizados", value=f"{pico:,}", delta="+")
        else:
            st.metric(label="Hospitalizados Promedio", value=int(df_con_poblacion["hospitalizados"].mean()), delta="")
    
    # Gráficos principales
    st.header("📈 Análisis por Estado y Región")
    
    col1, col2 = st.columns(2)
    
    with col1:
        metrica_col1 = "casos" if metrica == "casos" else "muertes"
        fig_ranking = grafico_ranking(df_con_poblacion, metrica)
        st.plotly_chart(fig_ranking, use_container_width=True)
    
    with col2:
        fig_evolution = grafico_evolution(
            df_con_poblacion, 
            metrica, 
            fecha_inicio=fecha_inicio if "fecha" in df_con_poblacion.columns else None,
            fecha_fin=fecha_fin if "fecha" in df_con_poblacion.columns else None
        )
        st.plotly_chart(fig_evolution, use_container_width=True)
    
    # Gráfico de hospitalizados (sección aparte)
    if metrica == "hospitalizados":
        st.header("🏥 Hospitalizados por Estado/Región")
        fig_hospital = grafico_hospitalizados(df_con_poblacion)
        st.plotly_chart(fig_hospital, use_container_width=True)
    
    # Tabla de resumen (opcional)
    with st.expander("📋 Ver tabla completa"):
        df_display = df_con_poblacion[[
            "fecha", "estado", "casos", "muertes", 
            "hospitalizados" if "hospitalizados" in df_con_poblacion.columns else None
        ].dropna()]
        st.dataframe(df_display.head(100), hide_index=True)
    
    # Footer con créditos
    st.markdown("---")
    st.caption("""
    🦠 **COVID-19 Dashboard** | Fuente: The COVID Tracking Project & US Census Bureau
    """)

if __name__ == "__main__":
    main()
"""