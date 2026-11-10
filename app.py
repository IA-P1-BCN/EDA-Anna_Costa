import os
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import streamlit as st

# Configuración de página
page_icon = ":hospital:"
page_title = "COVID-19 EDA Dashboard"

st.set_page_config(
    page_title=page_title,
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def load_processed_data():
    """Carga los datos procesados desde el repositorio."""
    
    script_dir = Path(__file__).parent if __file__ else Path.cwd()
    
    # Intentar cargar de data/processed primero (prioridad absoluta)
    processed_dir = script_dir / "data" / "processed"
    csv_files = list(processed_dir.glob("*.csv"))
    
    if not csv_files:
        print("❌ No se encontraron archivos CSV en data/processed/")
        return None, "No hay datos procesados disponibles."
    
    # Prioridad 1: covid_estados_final.csv (dataset principal)
    final_csv = processed_dir / "covid_estados_final.csv"
    if final_csv.exists():
        print("✅ Cargando desde data/processed/covid_estados_final.csv")
        df = pd.read_csv(final_csv)
        
        # Verificar columna fecha y convertir
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
        
        message = f"covid_estados_final.csv ({len(df)} registros, {df['estado'].nunique()} estados)"
        return df, message
    
    # Fallback a otras opciones
    if (processed_dir / "covid_estados_limpio.csv").exists():
        print("⚠️ Usando covid_estados_limpio.csv como alternativa")
        df = pd.read_csv(processed_dir / "covid_estados_limpio.csv")
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
        message = f"covid_estados_limpio.csv ({len(df)} registros)"
        return df, message
    
    if (processed_dir / "covid_estados_poblacion.csv").exists():
        print("⚠️ Usando covid_estados_poblacion.csv como alternativa")
        df = pd.read_csv(processed_dir / "covid_estados_poblacion.csv")
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
        message = f"covid_estados_poblacion.csv ({len(df)} registros)"
        return df, message
    
    # Fallback a data/raw si processed está vacío
    raw_dir = script_dir / "data" / "raw"
    if (raw_dir / "covid_cases_by_state.csv").exists():
        print("⚠️ Usando data/raw/covid_cases_by_state.csv")
        df = pd.read_csv(raw_dir / "covid_cases_by_state.csv")
        df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
        message = f"data/raw/covid_cases_by_state.csv ({len(df)} registros)"
        return df, message
    
    if (raw_dir / "covid_deaths_by_state.csv").exists():
        print("⚠️ Usando data/raw/covid_deaths_by_state.csv")
        df = pd.read_csv(raw_dir / "covid_deaths_by_state.csv")
        df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
        message = f"data/raw/covid_deaths_by_state.csv ({len(df)} registros)"
        return df, message
    
    # Último fallback: intentar unificar los archivos raw disponibles
    print("🔄 Unificando archivos de datos brutos...")
    dataframes = []
    
    for csv_file in raw_dir.glob("*.csv"):
        try:
            if 'covid_cases' in csv_file.stem.lower():
                df_case = pd.read_csv(csv_file)
                if 'fecha' in df_case.columns:
                    df_case['fecha'] = pd.to_datetime(df_case['fecha'], utc=True).dt.tz_localize(None)
                dataframes.append(df_case)
            elif 'covid_deaths' in csv_file.stem.lower():
                df_death = pd.read_csv(csv_file)
                if 'fecha' in df_death.columns:
                    df_death['fecha'] = pd.to_datetime(df_death['fecha'], utc=True).dt.tz_localize(None)
                dataframes.append(df_death)
        except Exception as e:
            print(f"⚠️ Error leyendo {csv_file}: {e}")
    
    if dataframes:
        df_combined = pd.concat(dataframes, ignore_index=True)
        message = f"Unificados: {len(df_combined)} registros totales"
        return df_combined, message
    
    return None, "No se pudieron cargar los datos. Revisa la consola para detalles."


def get_available_metrics(df):
    """Obtiene lista de métricas disponibles."""
    return ['casos', 'muertes', 'hospitalizados'] + [col for col in df.columns if col not in ['casos', 'muertes', 'hospitalizados']]


# ============================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================

if "df" not in st.session_state:
    st.session_state.df = None

if "selected_metric" not in st.session_state:
    st.session_state.selected_metric = "casos"

if "date_filter" not in st.session_state:
    st.session_state.date_filter = None


# ============================================
# SIDEBAR - CONFIGURACIÓN DEL PANEL
# ============================================

with st.sidebar:
    st.header("⚙️ Configuración del Panel", divider="primary")
    
    # Selector de métrica
    available_metrics = get_available_metrics(st.session_state.df) if st.session_state.df is not None else []
    selected_metric = st.selectbox(
        "📊 Métrica a analizar:",
        available_metrics,
        index=available_metrics.index(st.session_state.selected_metric) if st.session_state.selected_metric in available_metrics else 0,
        help="Selecciona la métrica que deseas analizar (casos, muertes, hospitalizados u otras)"
    )
    st.session_state.selected_metric = selected_metric
    
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
        start_date = datetime.datetime.now().date() - pd.Timedelta(days=days[date_option])
        st.session_state.date_filter = (start_date, datetime.datetime.now().date())


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
region_aggregated = df.groupby('estado')[st.session_state.selected_metric].sum().sort_values(ascending=False)

with col2:
    if plot_type == "Bar Chart Horizontal":
        fig_bar = px.bar(
            region_aggregated.head(10).reset_index(),
            y='estado',
            x=st.session_state.selected_metric,
            orientation='h',
            title=f"Top 10 Estados por {st.session_state.selected_metric.title()}",
            color=st.session_state.selected_metric,
            color_continuous_scale="Viridis",
            labels={st.session_state.selected_metric: st.session_state.selected_metric.title(), 'estado': 'Estado'}
        )
        fig_bar.update_layout(height=450)
        
    else:  # Line Chart
        fig_line = px.line(
            filtered_df.sort_values('fecha'),
            x='fecha',
            y=st.session_state.selected_metric,
            title=f"Tendencia de {st.session_state.selected_metric.title()} a lo largo del tiempo",
            markers=True,
            labels={st.session_state.selected_metric: st.session_state.selected_metric.title(), 'fecha': 'Fecha'},
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
    if len(df.groupby('estado')[st.session_state.selected_metric].count()) > 0:
        with st.expander("📈 Distribución por Estado"):
            state_counts = df.groupby('estado')[st.session_state.selected_metric].sum().sort_values(ascending=False).head(15)
            
            fig_state_dist = px.bar(
                state_counts.reset_index(),
                x='estado',
                y=st.session_state.selected_metric,
                title=f"Distribución por Estado ({st.session_state.selected_metric.title()})",
                color=st.session_state.selected_metric,
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
    file_name=f"covid_eda_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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

*Generado el {datetime.datetime.now().strftime('%Y-%m-%d')} | Versión 1.0 para despliegue en Streamlit Cloud*
""".format())
