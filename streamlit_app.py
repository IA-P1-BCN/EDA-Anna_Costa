"""App Streamlit para el dashboard de COVID-19 en Estados Unidos (2020-2021).

Requisitos:
  - Python 3.8+
  - pandas, numpy, plotly, requests, streamlit

Para ejecutar localmente:
  python streamlit_app.py

Para desplegar en Streamlit Cloud:
  1. Sube este archivo a GitHub (en un repo público)
  2. Conecta el repo a https://streamlit.io/cloud
"""

import subprocess
import sys
from datetime import datetime, timedelta

# Descargar dependencias si es necesario
try:
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import requests
except ImportError:
    print("Instalando dependencias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pandas", "numpy", "plotly", "requests"])
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import requests


# ============================================
# PASO 1: Descargar y preparar los datos desde GitHub
# ============================================

def descargar_datos():
    """Descarga los CSVs de COVID Tracking Project."""
    
    # URL oficial del dataset agregado por estado
    url_covid = "https://raw.githubusercontent.com/COVIDTracking/covid_open_data_processing/master/data/aggregated_state_daily.csv"
    
    print("⏳ Descargando datos de COVID Tracking Project...")
    
    try:
        resp = requests.get(url_covid, timeout=30)
        if resp.status_code == 200:
            df_covid = pd.read_csv(resp.text, skiprows=1)
            print(f"✓ Descargado con éxito ({len(df_covid)} registros)")
            
            # Mostrar las primeras columnas para verificar
            print("\n📊 Columnas disponibles:")
            for col in df_covid.columns[:10]:  # Solo mostrar primeras 10 columnas
                print(f"  - {col}")
            return df_covid
        else:
            print(f"⚠ No se pudo descargar (status: {resp.status_code})")
            return None
    except Exception as e:
        print(f"⚠ Error al descargar: {e}")
        return None


# ============================================
# PASO 2: Funciones simplificadas de visualización con Plotly
# ============================================

def grafico_evolucion(df, metrica, fecha_inicio, fecha_fin):
    """Gráfico interactivivo de evolución temporal usando Plotly."""
    columnas_metricas = ["casos", "muertes", "hospitalizados"]
    
    if metrica not in columnas_metricas:
        metrica = "casos"
    
    # Filtrar por rango de fechas
    df_filtrado = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)]
    
    # Crear gráfico de Plotly
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_filtrado["fecha"],
        y=df_filtrado[metrica],
        mode='lines+markers',
        name=metrica.capitalize(),
        line=dict(color='#2a78d6', width=2)
    ))
    
    fig.update_layout(
        title=f"Evolución de {metrica.upper()} en EE.UU.",
        xaxis_title="Fecha",
        yaxis_title=metrica.capitalize(),
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig


def grafico_ranking(df, metrica):
    """Gráfico de barras con ranking por estado."""
    columnas_metricas = ["casos", "muertes"]
    
    if metrica not in columnas_metricas:
        metrica = "casos"
    
    # Agrupar y ordenar por estado
    ranking = df.groupby("estado")[metrica].sum().nlargest(10)
    ranking_df = pd.DataFrame({'estado': ranking.index, 'valor': ranking.values})
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=metrica.capitalize(),
        x=ranking_df['estado'],
        y=ranking_df['valor'],
        marker_color='#2a78d6',
        orientation='h'
    ))
    
    fig.update_layout(
        title=f"Top 10 Estados por {metrica.upper()}",
        yaxis={'categoryorder': 'total ascending'},
        template='plotly_white'
    )
    
    return fig


def grafico_mapa_estados(df):
    """Gráfico simple de casos por estado."""
    df_agregado = df.groupby("estado").agg({
        "casos": ["sum", "count"],
        "muertes": "sum"
    }).reset_index()
    
    df_agregado.columns = ['estado', 'total_casos', 'n_dias', 'total_muertes']
    df_agregado = df_agregado[df_agregado['n_dias'] > 0].head(10)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_agregado['estado'],
        y=df_agregado['total_casos'],
        name='Casos',
        marker_color='#2a78d6'
    ))
    
    fig.update_layout(
        title="Top 10 Estados con Más Casos",
        template='plotly_white'
    )
    
    return fig


# ============================================
# PASO 3: Función principal de la app Streamlit
# ============================================

def main():
    """Función principal que renderiza el dashboard."""
    
    import streamlit as st
    
    # Configurar la página
    st.set_page_config(
        page_title="COVID-19 Dashboard EE.UU.",
        page_icon="🦠",
        layout="wide"
    )
    
    # Título y descripción
    st.title("📊 COVID-19 en Estados Unidos (2020-2021)")
    st.markdown("""
    Este dashboard interactivo muestra los datos de COVID-19 en Estados Unidos desde marzo de 2020 hasta julio de 2021.
    
    **Fuentes de datos**:
    - [The COVID Tracking Project](https://covidtracking.com/) (casos, muertes, hospitalizados)
    - Licencia: CC BY 4.0
    """)
    
    # Botón para descargar y cargar datos
    if st.button("📥 Descargar Cargar Datos", type="primary"):
        df_covid = descargar_datos()
        if df_covid is not None:
            st.success(f"✓ Se cargaron {len(df_covid)} registros de COVID-19")
            # Guardar en sesión
            st.session_state['df_data'] = df_covid
    elif 'df_data' in st.session_state:
        df_covid = st.session_state['df_data']
    
    if 'df_data' not in st.session_state:
        st.warning("⚠ Por favor, haz clic en 'Descargar y Cargar Datos' para comenzar.")
        return
    
    # Panel lateral con filtros
    with st.sidebar:
        st.header("🎛️ Filtros")
        
        # Selector de métrica
        metrica = st.selectbox(
            "Seleccionar métrica:",
            ["casos", "muertes", "hospitalizados"],
            help="Elige qué métrica deseas visualizar"
        )
        
        # Selector de rango temporal
        fecha_fin = st.date_input(
            "Fecha final:", 
            value=datetime.now(),
            max_value=datetime.now()
        )
        fecha_inicio = st.date_input(
            "Fecha inicial:", 
            value=fecha_fin - timedelta(days=365),
            min_value=df_covid["fecha"].min(),
            max_value=fecha_fin
        )
        
        # Información de los datos
        st.divider()
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.metric("Total Registros", len(df_covid))
        with info_col2:
            estados_unicos = df_covid["estado"].nunique()
            st.metric("Estados con Datos", estados_unicos)
        
        st.divider()
        st.info("""
        📚 **Información**
        - Datos oficiales de COVID Tracking Project
        - Actualizados semanalmente
        
        🔗 [Ver código en GitHub](https://github.com/IA-P1-BCN/EDA-Anna_Costa)
        """)
    
    # Panel principal con gráficos
    st.header(f"📈 Análisis de {metrica.upper()} por Estado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_evolucion = grafico_evolucion(df_covid, metrica, fecha_inicio.date(), fecha_fin.date())
        st.plotly_chart(fig_evolucion, use_container_width=True)
    
    with col2:
        # Filtrar por rango y mostrar ranking
        df_filtrado = df_covid[(df_covid["fecha"] >= fecha_inicio.date()) & 
                               (df_covid["fecha"] <= fecha_fin.date())]
        fig_ranking = grafico_ranking(df_filtrado, metrica)
        st.plotly_chart(fig_ranking, use_container_width=True)
    
    # Mostrar top estados
    st.header("🏆 Top 10 Estados (Ranking)")
    df_top = df_covid.groupby("estado").agg({
        "casos": "sum",
        "muertes": "sum",
        "hospitalizados": "sum"
    }).nlargest(10, "casos").reset_index()
    
    st.dataframe(df_top.head(10), hide_index=True)


# Ejecutar la app si es el script principal
if __name__ == "__main__":
    main()
"""
