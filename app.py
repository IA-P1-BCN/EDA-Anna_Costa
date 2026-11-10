import os
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import streamlit as st
import unicodedata

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
    metric_columns = [col for col in df.columns if col not in ['casos', 'muertes', 'hospitalizados']]
    return ['casos', 'muertes', 'hospitalizados'] + metric_columns


def format_metric_name_for_display(metric_name):
    """Formatea el nombre de la métrica para mostrarla de forma legible."""
    if pd.isna(metric_name) or not isinstance(metric_name, str):
        return str(metric_name)
    
    try:
        # Normalizar Unicode (descompone caracteres acentuados)
        normalized = unicodedata.normalize('NFD', metric_name)
        
        # Quitar acentos y espacios adicionales
        metric_clean = ''.join(ch.replace('\u0301', '').replace(' ', '') for ch in normalized)
        
        # Capitalizar cada palabra (excepto artículos/preposiciones cortas)
        words = metric_clean.lower().split()
        capitalized_words = []
        
        stop_words = {'de', 'la', 'el', 'y', 'al', 'en', 'un', 'una', 'con', 'para'}
        
        for word in words:
            if len(word) > 2 and word not in stop_words:
                capitalized_words.append(word.capitalize())
            else:
                capitalized_words.append(word)
        
        return ' '.join(capitalized_words)
    except Exception as e:
        print(f"⚠️ Error formateando métrica {metric_name}: {e}")
        return str(metric_name)


# ============================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================

def initialize_session_state():
    """Inicializa el session state con valores por defecto si no existen."""
    
    # Inicializar dataframe (si existe, mantenerlo; sino None)
    if "df" not in st.session_state:
        st.session_state.df = None
    
    # Inicializar métrica seleccionada
    if "selected_metric" not in st.session_state:
        st.session_state.selected_metric = "casos"
    
    # Inicializar filtro temporal (si existe, mantenerlo; sino None)
    if "date_filter" not in st.session_state:
        st.session_state.date_filter = None
    
    return True


# ============================================
# SIDEBAR - CONFIGURACIÓN DEL PANEL
# ============================================

with st.sidebar:
    st.header("⚙️ Configuración del Panel", divider="primary")
    
    # Selector de métrica (si hay datos cargados)
    if st.session_state.df is not None:
        available_metrics = get_available_metrics(st.session_state.df)
        
        if available_metrics:
            selected_metric = st.selectbox(
                "📊 Métrica a analizar:",
                available_metrics,
                index=0 if not st.session_state.selected_metric or st.session_state.selected_metric not in available_metrics else 
                       available_metrics.index(st.session_state.selected_metric),
                help="Selecciona la métrica que deseas analizar (casos, muertes, hospitalizados u otras)"
            )
            st.session_state.selected_metric = selected_metric
    
    # Filtros temporales
    st.subheader("📅 Período Temporal")
    
    if st.session_state.df is not None:
        last_data_date = st.session_state.df['fecha'].max()
        
        date_option = st.radio(
            "Rango temporal:",
            ["Completo", "-30 días", "-60 días", "-90 días"],
            horizontal=True,
            key="date_filter_radio"  # Clave única para forzar recálculo
        )
        
        if date_option == "Completo":
            st.session_state.date_filter = None
            st.info("✅ Se mostrarán todos los datos disponibles")
        else:
            days = {"-30 días": 30, "-60 días": 60, "-90 días": 90}
            
            # 🔴 CORRECCIÓN CRÍTICA: Usar la última fecha del dataset, NO hoy en día
            end_date = last_data_date.date()  # Fecha final del dataset (ej: 2021-12-31)
            start_date = last_data_date - pd.Timedelta(days=days[date_option])
            
            st.session_state.date_filter = (start_date, end_date)
            
            # Mostrar rango seleccionado
            st.caption(
                f"📌 Rango: {start_date.date().strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}"
            )
    else:
        st.warning("⚠️ Esperando datos para mostrar filtros temporales")


# ============================================
# CARGA DE DATOS (UNA SOLA VEZ)
# ============================================

df_loaded = None

if st.session_state.df is None:
    try:
        st.session_state.df, load_message = load_processed_data()
        
        if st.session_state.df is not None:
            df_loaded = st.session_state.df
            st.success(f"✅ {load_message}")
            
            # Calcular estadísticas básicas para mostrar en cards
            total_records = len(df_loaded)
            unique_states = df_loaded['estado'].nunique() if 'estado' in df_loaded.columns else 0
            
            # Fecha mínima y máxima
            if 'fecha' in df_loaded.columns:
                min_date = df_loaded['fecha'].min().strftime('%d/%m/%Y')
                max_date = df_loaded['fecha'].max().strftime('%d/%m/%Y')
                total_days = (df_loaded['fecha'].max() - df_loaded['fecha'].min()).days + 1
            else:
                min_date = "N/A"
                max_date = "N/A"
                total_days = 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Registros Cargados", f"{total_records:,}", delta="OK")
            
            with col2:
                st.metric("Estados", unique_states, delta="Active")
            
            with col3:
                st.metric("Días Periodo", total_days, delta="Cobertura")
            
            with col4:
                st.metric("Fuente", "data/processed/", delta="Directo")
        else:
            st.error("❌ No se pudieron cargar los datos. Revisa la consola para detalles.")
            st.stop()
            
    except Exception as e:
        st.error(f"❌ Error crítico al cargar datos:\n\n{str(e)[:200]}")
        st.stop()

# Actualizar session_state con dataframe cargado
st.session_state.df = df_loaded


# ============================================
# SECCIÓN 1: MÉTRICAS CLAVE DEL PERÍODO (RENDERIZADO CON NÚMERO DE SECCIÓN PARA FORZAR RECALCULO)
# ============================================

with st.container():
    st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📈 Métricas Clave del Período</h3>', unsafe_allow_html=True)
    
    # Aplicar filtros temporales SI EXISTEN (cada vez que se renderiza)
    if st.session_state.date_filter:
        start_date, end_date = st.session_state.date_filter
        mask = (df_loaded['fecha'] >= start_date) & (df_loaded['fecha'] <= end_date)
        filtered_df = df_loaded[mask].copy()
    else:
        filtered_df = df_loaded.copy()
    
    # Verificar que no esté vacío
    if filtered_df.empty:
        st.error("⚠️ No hay datos para mostrar con los filtros seleccionados.")
    elif 'casos' in filtered_df.columns:
        total_casos = filtered_df['casos'].sum()
        has_muertes = 'muertes' in filtered_df.columns
        has_hospitalizados = 'hospitalizados' in filtered_df.columns
        
        if has_muertes:
            total_muertes = filtered_df.get('muertes').sum()
        else:
            total_muertes = 0
        
        if has_hospitalizados:
            total_hospitalizados = filtered_df['hospitalizados'].sum()
        else:
            total_hospitalizados = 0
        
        # Calcular tasas
        tasa_fatality = (total_muertes / total_casos * 100) if total_casos > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📋 Casos Totales", 
                f"{total_casos:,}", 
                help=f"Suma total de casos confirmados en el periodo"
            )
        
        with col2:
            st.metric(
                "⚰️ Muertes Confirmadas", 
                f"{total_muertes:,}", 
                delta=f"{tasa_fatality:.2f}%",
                help="Tasa de letalidad calculada sobre casos totales"
            )
        
        with col3:
            if has_hospitalizados and total_hospitalizados > 0:
                st.metric(
                    "🏥 Pacientes Hospitalizados", 
                    f"{total_hospitalizados:,}", 
                    help="Total de pacientes activos en hospitales"
                )
            else:
                st.info("ℹ️ No hay datos de hospitalizaciones disponibles")
        
        with col4:
            if 'poblacion_total' in filtered_df.columns and filtered_df['poblacion_total'].sum() > 0:
                media_casos_poc = total_casos / filtered_df['poblacion_total'].sum()
                st.metric(
                    "👥 Casos por Hab./Medio", 
                    f"{media_casos_poc:.2f}",
                    help="Casos promedio por habitante"
                )


# ============================================
# SECCIÓN 2: MAPA DE CASOS POR ESTADO
# ============================================

with st.container():
    st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">🗺️ Mapa de Casos por Estado</h3>', unsafe_allow_html=True)
    
    if 'casos' in filtered_df.columns and 'estado' in filtered_df.columns:
        # Ordenar por casos y tomar top 15 (RECALCULADO CADA VEZ)
        state_cases = filtered_df.groupby('estado')['casos'].sum().sort_values(ascending=False).head(15)
        
        fig_state_map = px.bar(
            state_cases.reset_index(),
            x='estado',
            y='casos',
            orientation='h',
            title=f"Top 15 Estados por Casos Totales",
            color='casos',
            color_continuous_scale="Blues"
        )
        fig_state_map.update_layout(height=400)
        
        st.plotly_chart(fig_state_map, use_container_width=True)


# ============================================
# SECCIÓN 3: TENDENCIAS TEMPORALES
# ============================================

with st.container():
    st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📅 Tendencias Temporales</h3>', unsafe_allow_html=True)
    
    if 'casos' in filtered_df.columns and 'fecha' in filtered_df.columns:
        # Ordenar por fecha y agregar acumulados semanales (RECALCULADO CADA VEZ)
        df_temporal = filtered_df.sort_values('fecha').groupby(['fecha', 'estado'], as_index=False)['casos'].sum()
        
        fig_trends = px.line(
            df_temporal, 
            x='fecha', 
            y='casos', 
            color='estado',
            title="Evolución de Casos Temporales",
            markers=True
        )
        fig_trends.update_layout(height=400)
        
        st.plotly_chart(fig_trends, use_container_width=True)


# ============================================
# SECCIÓN 4: ANÁLISIS POR VARIABLES (DINÁMICO SEGÚN MÉTRICA SELECCIONADA)
# ============================================

with st.container():
    st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">🔍 Análisis Detallado de Variables</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Tabla resumen estadístico para variables numéricas (RECALCULADA CADA VEZ)
        numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
        
        if numeric_cols:
            with st.expander("📊 Ver resumen estadístico completo"):
                summary_df = pd.DataFrame({
                    "Variable": numeric_cols,
                    "Media": [filtered_df[col].mean() for col in numeric_cols],
                    "Mediana": [filtered_df[col].median() for col in numeric_cols],
                    "Mínimo": [filtered_df[col].min() for col in numeric_cols],
                    "Máximo": [filtered_df[col].max() for col in numeric_cols],
                    "Desviación Estándar": [filtered_df[col].std() for col in numeric_cols]
                })
                
                # Filtrar NaN e infinito y redondear
                summary_df = summary_df.replace([np.inf, -np.inf], np.nan).round(2)
                
                st.dataframe(summary_df, use_container_width=True, height=300)
    
    with col2:
        # Mostrar distribución de valores por estado (para variable seleccionada)
        # 🔴 CLAVE: Se ejecuta con la NUEVA métrica cada vez que se renderiza el contenedor
        if filtered_df is not None and st.session_state.selected_metric:
            metric_col = st.session_state.selected_metric
            
            # Verificar que no sea una métrica numérica (casos, muertes, hospitalizados)
            if metric_col not in ['casos', 'muertes', 'hospitalizados']:
                if metric_col in filtered_df.columns:
                    state_counts = filtered_df.groupby('estado')[metric_col].sum().sort_values(ascending=False).head(15)
                    
                    fig_state_dist = px.bar(
                        state_counts.reset_index(),
                        x='estado',
                        y=metric_col,
                        title=f"Distribución por Estado ({format_metric_name_for_display(metric_col.title())})",
                        color=metric_col,
                        color_continuous_scale="Blues"
                    )
                    fig_state_dist.update_layout(height=350)
                    
                    st.plotly_chart(fig_state_dist, use_container_width=True)


# ============================================
# SECCIÓN 5: DESCARGA DE DATOS
# ============================================

with st.container():
    st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">💾 Exportar Datos</h3>', unsafe_allow_html=True)
    
    csv_buffer = filtered_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
    
    st.download_button(
        label="📥 Descargar datos filtrados (CSV)",
        data=csv_buffer,
        file_name=f"covid_eda_{filtered_df['estado'].nunique()}_estados_{start_date.date().strftime('%d%m%Y')}-{end_date.strftime('%d%m%Y')}.csv" if st.session_state.date_filter else f"covid_eda_{filtered_df['estado'].nunique()}_estados_completo.csv",
        mime="text/csv",
        help="Descarga el conjunto completo de datos procesados para análisis externo"
    )


# ============================================
# SECCIÓN 6: NOTAS METODológicas Y FUENTES
# ============================================

with st.container():
    st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📝 Notas Metodológicas</h3>', unsafe_allow_html=True)
    
    st.markdown(f"""
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

**🔴 IMPORTANTE - Filtrado Temporal:**
Los filtros temporales aplican rangos **relativos a la última fecha disponible del dataset**, no a "hoy". Esto evita mostrar NaN al analizar datos históricos.
""".format())

# Footer con información del proyecto
st.markdown("---")
st.caption(f"""
🦠 **COVID-19 EDA Dashboard** | Proyecto IA P1-BCN Maestría 2º | Análisis Exploratorio de Datos

*Generado el {datetime.datetime.now().strftime('%Y-%m-%d')} | Versión 1.2 - Corrección de recálculo dinámico aplicada*
""")