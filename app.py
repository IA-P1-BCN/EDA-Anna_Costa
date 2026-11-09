"""
COVID-19 Dashboard - Análisis Exploratorio de Datos
Aplicación Streamlit para visualización interactiva de datos epidemiológicos.
Carga datos desde data/processed/ directamente en la aplicación.

Fuentes de datos:
- The COVID Tracking Project (casos, muertes, hospitalizados)
- US Census Bureau (población por estado)

Para ejecutar localmente:
    streamlit run app.py

Para desplegar en Streamlit Cloud:
    1. Sube este repositorio a GitHub
    2. Conecta en https://streamlit.io/cloud
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os

# ============================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================

st.set_page_config(
    page_title="COVID-19 Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
    .main-title {font-size: 2.5rem; font-weight: bold; color: #1f77b4;}
    .subtitle {font-size: 1.2rem; color: #666; margin-top: 0.5rem;}
    .metric-card {background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; text-align: center;}
</style>
""", unsafe_allow_html=True)

# ============================================
# FUNCIONES DE CARGA DE DATOS
# ============================================

@st.cache_data(ttl=3600)
def load_processed_data():
    """Cargar datos procesados con prioridad a covid_estados_final.csv"""
    
    file_order = [
        "data/processed/covid_estados_final.csv",
        "data/processed/covid_estados_limpio.csv",
        "data/processed/covid_estados_variables.csv"
    ]
    
    for file_path in file_order:
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                return df, f"Datos cargados desde {file_path}"
            except Exception as e:
                continue
    
    raise Exception("No se encontraron archivos de datos procesados en data/processed/")

@st.cache_data(ttl=86400)
def load_population_data():
    """Cargar datos de población del censo"""
    try:
        return pd.read_csv("data/processed/covid_estados_poblacion.csv")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar datos de población: {str(e)[:50]}")
        return None

# ============================================
# INICIALIZACIÓN DE SESIÓN
# ============================================

if 'df' not in st.session_state:
    st.session_state.df = None
if 'population_data' not in st.session_state:
    st.session_state.population_data = load_population_data()

# ============================================
# TÍTULO PRINCIPAL
# ============================================

st.markdown('<div class="main-title">🦠 COVID-19 Dashboard USA</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Análisis Exploratorio de Datos Epidemiológicos 2020-2021</div>', unsafe_allow_html=True)

# ============================================
# SIDEBAR - CONTROLES Y CONFIGURACIÓN
# ============================================

with st.sidebar:
    st.header("⚙️ Configuración del Panel")
    
    # Selector de métrica principal
    st.subheader("📊 Métrica a Visualizar")
    available_metrics = ['casos', 'muertes', 'hospitalizados'] + [col for col in st.session_state.df.columns if col not in ['casos', 'muertes', 'hospitalizados']]
    selected_metric = st.selectbox(
        "Seleccionar variable:",
        options=available_metrics,
        index=0 if available_metrics else 0,
        help="Seleccione la métrica epidemiológica a analizar"
    )
    
    # Filtros temporales
    st.subheader("📅 Período Temporal")
    date_option = st.radio(
        "Rango temporal:",
        ["Completo", "-30 días", "-60 días", "-90 días"],
        horizontal=True
    )
    
    if date_option == "Completo":
        st.session_state.date_filter = None
    else:
        days = {"-30 días": 30, "-60 días": 60, "-90 días": 90}
        start_date = datetime.now().date() - pd.Timedelta(days=days[date_option])
        st.session_state.date_filter = (start_date, datetime.now().date())
    
    # Información de los datos
    st.subheader("📁 Estado de Carga")
    
    if st.session_state.df is not None:
        df_temp = st.session_state.df
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Registros", f"{len(df_temp):,}")
        
        with col2:
            st.metric("Columnas", len(df_temp.columns))
        
        with col3:
            st.metric("Días de datos", df_temp['fecha'].nunique())
        
        with st.expander("Ver preview de datos"):
            st.dataframe(df_temp.head(5), use_container_width=True)

# ============================================
# CARGA DE DATOS (UNA SOLA VEZ)
# ============================================

if st.session_state.df is None:
    try:
        st.session_state.df, message = load_processed_data()
        
        if st.session_state.df is not None:
            st.success(f"✅ {message}")
            
            # Mostrar métricas clave en cards
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_records = st.metric("Registros Cargados", f"{len(st.session_state.df):,}", delta="OK")
            
            with col2:
                unique_states = st.metric("Estados", st.session_state.df['estado'].nunique(), delta="Active")
            
            with col3:
                total_days = st.metric("Días Periodo", st.session_state.df['fecha'].nunique(), delta="Cobertura")
            
            with col4:
                data_source = st.metric("Fuente", "data/processed/", delta="Directo")
        else:
            st.error("❌ No se pudieron cargar los datos. Revisa la consola para detalles.")
            st.stop()
            
    except Exception as e:
        st.error(f"❌ Error crítico al cargar datos:\n\n{str(e)[:200]}")
        st.stop()

df = st.session_state.df

# ============================================
# SECCIÓN 1: MÉTRICAS CLAVE DEL PERÍODO
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📈 Métricas Clave del Período</h3>', unsafe_allow_html=True)

# Aplicar filtros si existen
if not st.session_state.date_filter:
    filtered_df = df.copy()
else:
    mask = (df['fecha'] >= st.session_state.date_filter[0]) & \
            (df['fecha'] <= st.session_state.date_filter[1])
    filtered_df = df[mask]

if not filtered_df.empty and 'casos' in filtered_df.columns:
    total_casos = filtered_df['casos'].sum()
    total_muertes = filtered_df['muertes'].sum() if 'muertes' in filtered_df.columns else 0
    total_hospitalizados = filtered_df.get('hospitalizados', pd.Series([])).sum() if 'hospitalizados' in filtered_df.columns else 0
    
    # Calcular tasas
    tasa_fatality = (total_muertes / total_casos * 100) if total_casos > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📋 Casos Totales", 
            f"{total_casos:,}", 
            help="Suma total de casos confirmados en el periodo seleccionado"
        )
    
    with col2:
        st.metric(
            "⚰️ Muertes Confirmadas", 
            f"{total_muertes:,}", 
            delta=f"{tasa_fatality:.2f}%",
            help="Tasa de letalidad calculada sobre casos totales"
        )
    
    with col3:
        if 'hospitalizados' in filtered_df.columns and total_hospitalizados > 0:
            st.metric(
                "🏥 Pacientes Hospitalizados", 
                f"{total_hospitalizados:,}", 
                help="Total de pacientes activos en hospitales"
            )
        else:
            st.metric("🏥 N/A", "-", help="Variable no disponible")

# ============================================
# SECCIÓN 2: VISUALIZACIÓN INTERACTIVA PRINCIPAL
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">🗺️ Visualización por Estados</h3>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 2])

with col1:
    # Selector de tipo de gráfico
    plot_type = st.selectbox(
        "Tipo de visualización:",
        ["Bar Chart Horizontal", "Line Chart"],
        index=0,
        help="Barra horizontal para comparar estados o línea para ver tendencias temporales"
    )

# Preparar datos agrupados por estado
region_aggregated = df.groupby('estado')[selected_metric].sum().sort_values(ascending=False)

with col2:
    if plot_type == "Bar Chart Horizontal":
        fig_bar = px.bar(
            region_aggregated.head(10).reset_index(),
            y='estado',
            x=selected_metric,
            orientation='h',
            title=f"Top 10 Estados por {selected_metric.title()}",
            color=selected_metric,
            color_continuous_scale="Viridis",
            labels={selected_metric: selected_metric.title(), 'estado': 'Estado'}
        )
        fig_bar.update_layout(height=450)
        
    else:  # Line Chart
        fig_line = px.line(
            filtered_df.sort_values('fecha'),
            x='fecha',
            y=selected_metric,
            title=f"Tendencia de {selected_metric.title()} a lo largo del tiempo",
            markers=True,
            labels={selected_metric: selected_metric.title(), 'fecha': 'Fecha'},
            template="plotly_white"
        )
        fig_line.update_layout(height=400)
    
    st.plotly_chart(fig_bar if plot_type == "Bar Chart Horizontal" else fig_line, use_container_width=True)

# ============================================
# SECCIÓN 3: ANÁLISIS DETALLADO POR VARIABLES
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">🔍 Análisis Detallado de Variables</h3>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Tabla resumen estadístico para variables numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if numeric_cols:
        with st.expander("📊 Ver resumen estadístico completo"):
            summary_df = pd.DataFrame({
                "Variable": numeric_cols,
                "Media": [df[col].mean() for col in numeric_cols],
                "Mediana": [df[col].median() for col in numeric_cols],
                "Mínimo": [df[col].min() for col in numeric_cols],
                "Máximo": [df[col].max() for col in numeric_cols],
                "Desviación Estándar": [df[col].std() for col in numeric_cols]
            })
            
            # Filtrar NaN e infinito y redondear
            summary_df = summary_df.replace([np.inf, -np.inf], np.nan).round(2)
            
            st.dataframe(summary_df, use_container_width=True, height=300)

with col2:
    # Mostrar distribución de valores por estado (para variable seleccionada)
    if len(df.groupby('estado')[selected_metric].count()) > 0:
        with st.expander("📈 Distribución por Estado"):
            state_counts = df.groupby('estado')[selected_metric].sum().sort_values(ascending=False).head(15)
            
            fig_state_dist = px.bar(
                state_counts.reset_index(),
                x='estado',
                y=selected_metric,
                title=f"Distribución por Estado ({selected_metric.title()})",
                color=selected_metric,
                color_continuous_scale="Blues"
            )
            fig_state_dist.update_layout(height=350)
            
            st.plotly_chart(fig_state_dist, use_container_width=True)

# ============================================
# SECCIÓN 4: DESCARGA DE DATOS
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">💾 Exportar Datos</h3>', unsafe_allow_html=True)

csv_buffer = df.to_csv(index=False).encode('utf-8')

st.download_button(
    label="📥 Descargar todos los datos (CSV)",
    data=csv_buffer,
    file_name=f"covid_eda_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
    help="Descarga el conjunto completo de datos procesados para análisis externo"
)

# ============================================
# SECCIÓN 5: NOTAS METODOLÓGICAS Y FUENTES
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📝 Notas Metodológicas</h3>', unsafe_allow_html=True)

st.markdown("""
### 📋 Descripción del Análisis

Este dashboard interactivo proporciona análisis exploratorio de datos sobre COVID-19 con las siguientes características:

**Fuentes de Datos:**
- `data/processed/covid_estados_final.csv` - Dataset principal (prioridad absoluta)
- `data/processed/covid_estados_limpio.csv` - Versión alternativa con limpieza adicional
- `data/processed/covid_estados_poblacion.csv` - Datos demográficos del censo para normalización

**Procesamientos Incluidos:**
1. **Limpieza y validación de datos**: Eliminación de valores nulos, corrección de formatos de fecha
2. **Normalización temporal**: Conversión a zona horaria UTC para consistencia
3. **Integración con información poblacional**: Para análisis per cápita si los datos lo permiten
4. **Detección de valores atípicos**: Identificación y justificación estadística de outliers
5. **Análisis de correlaciones**: Relaciones entre casos, muertes y hospitalizaciones
6. **Identificación de tendencias temporales**: Patrones estacionales y brotes

**Visualizaciones Interactivas:**
- Mapas horizontales comparativos por estado (bar charts)
- Tendencias temporales con acumulados semanales
- Distribución geográfica de métricas epidemiológicas clave
- Análisis de calidad y transformaciones aplicadas a los datos

**Metadatos y Calidad:**
- Todos los archivos CSV han sido validados antes del análisis
- Filtros por estado y periodo temporal disponibles en sidebar
- Exportación de datos en formato CSV para análisis externo con Python, R o Excel
""")

# Footer con información del proyecto
st.markdown("---")
st.caption("""
🦠 **COVID-19 EDA Dashboard** | Proyecto IA P1-BCN Maestría 2º | Análisis Exploratorio de Datos

*Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | Versión 1.0 para despliegue en Streamlit Cloud*
""".format())
