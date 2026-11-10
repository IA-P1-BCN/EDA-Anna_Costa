import pandas as pd
from pathlib import Path
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
# CARGA DE DATOS - UNA SOLA VEZ
# ============================================

@st.cache_data
def load_data():
    """Carga los datos procesados desde el repositorio."""
    script_dir = Path(__file__).parent if __file__ else Path.cwd()
    processed_dir = script_dir / "data" / "processed"
    
    final_csv = processed_dir / "covid_estados_final.csv"
    df = pd.read_csv(final_csv)
    
    # Convertir fecha
    df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
    
    message = f"covid_estados_final.csv ({len(df)} registros, {df['estado'].nunique()} estados)"
    return df, message

# ============================================
# INICIALIZACIÓN
# ============================================

if "df" not in st.session_state:
    try:
        st.session_state.df, load_msg = load_data()
        st.success(f"✅ {load_msg}")
        
        # Estadísticas rápidas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Registros", len(st.session_state.df))
        with col2:
            st.metric("Estados", st.session_state.df['estado'].nunique())
        with col3:
            last_date = st.session_state.df['fecha'].max()
            first_date = st.session_state.df['fecha'].min()
            st.metric("Días", (last_date - first_date).days + 1)
        with col4:
            min_d = st.session_state.df['fecha'].min().strftime('%d/%m/%Y')
            max_d = st.session_state.df['fecha'].max().strftime('%d/%m/%Y')
            st.metric("Rango", f"{min_d} - {max_d}")
    except Exception as e:
        st.error(f"❌ Error cargando datos: {str(e)[:200]}")
        st.stop()

df = st.session_state.df

# ============================================
# SIDEBAR - FILTROS
# ============================================

with st.sidebar:
    st.header("⚙️ Configuración", divider="primary")
    
    # Columnas disponibles para mostrar
    metric_columns = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales'] + \
                     [col for col in df.columns if col not in ['casos_acum', 'muertes_acum', 'hospitalizados_actuales']]
    
    selected_metric = st.selectbox(
        "📊 Métrica a analizar:",
        metric_columns,
        index=0,  # Por defecto casos_acum
        help="Selecciona la métrica que deseas visualizar"
    )
    
    st.session_state.selected_metric = selected_metric
    
    # Filtros temporales - CRÍTICO: Usar fecha max del dataset
    last_date = df['fecha'].max()
    date_option = st.radio(
        "📅 Período temporal:",
        ["Completo", "-30 días", "-60 días", "-90 días"],
        horizontal=True,
        key="date_picker"  # Clave única para recalcular
    )
    
    if date_option == "Completo":
        st.session_state.date_filter = None
    else:
        days_map = {"-30 días": 30, "-60 días": 60, "-90 días": 90}
        days = days_map[date_option]
        end_date = last_date.date()
        start_date = (last_date - pd.Timedelta(days=days)).date()
        st.session_state.date_filter = (start_date, end_date)
        
        st.caption(f"📌 {start_date} a {end_date}")


# ============================================
# APLICAR FILTROS Y CALCULAR DATOS
# ============================================

# Aplicar filtro temporal si existe
if st.session_state.date_filter:
    start_date, end_date = st.session_state.date_filter
    mask = (df['fecha'] >= pd.Timestamp(start_date)) & (df['fecha'] <= pd.Timestamp(end_date))
    filtered_df = df[mask].copy()  # .copy() evita aliasing
else:
    filtered_df = df.copy()

# Obtener métrica seleccionada
metric_col = st.session_state.selected_metric


# ============================================
# SECCIÓN 1: MÉTRICAS CLAVE
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📈 Métricas Clave</h3>')

if not filtered_df.empty and metric_col in filtered_df.columns:
    total = float(filtered_df[metric_col].sum())
    
    # Obtener otras métricas de forma segura
    if 'muertes_acum' in filtered_df.columns:
        deaths_total = float(filtered_df['muertes_acum'].sum())
        fatality_rate = (deaths_total / total * 100) if total > 0 else 0.0
    else:
        deaths_total = None
        fatality_rate = None
    
    if 'hospitalizados_actuales' in filtered_df.columns:
        hosp_total = float(filtered_df['hospitalizados_actuales'].sum())
    else:
        hosp_total = None
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            f"📋 {metric_col.replace('_', ' ').title()}",
            f"{int(round(total)):,}"
        )
    
    with col2:
        if deaths_total is not None:
            st.metric(
                "⚰️ Muertes Totales",
                f"{int(round(deaths_total)):,}",
                delta=f"{fatality_rate:.2f}%"
            )
        else:
            st.info("ℹ️ Sin datos de muertes")
    
    with col3:
        if hosp_total is not None:
            st.metric(
                "🏥 Hospitalizados",
                f"{int(round(hosp_total)):,}"
            )
        else:
            st.info("ℹ️ Sin datos de hospitalizaciones")
    
    with col4:
        if 'poblacion' in filtered_df.columns and filtered_df['poblacion'].sum() > 0:
            per_capita = total / filtered_df['poblacion'].sum()
            st.metric(
                "👥 Por Habitante",
                f"{per_capita:.2f}"
            )


# ============================================
# SECCIÓN 2: MAPA POR ESTADO
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">🗺️ Por Estado</h3>')

if metric_col in filtered_df.columns and 'estado' in filtered_df.columns:
    state_data = filtered_df.groupby('estado')[metric_col].sum().sort_values(ascending=False).head(15)
    
    fig = px.bar(
        state_data.reset_index(),
        x='estado',
        y=metric_col,
        orientation='h',
        title=f"Top 15 Estados por {metric_col.replace('_', ' ').title()}",
        color=metric_col,
        color_continuous_scale="Blues"
    )
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, use_container_width=True)


# ============================================
# SECCIÓN 3: TENDENCIAS TEMPORALES
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📅 Evolución Temporal</h3>')

if metric_col in filtered_df.columns and 'fecha' in filtered_df.columns:
    temporal_data = filtered_df.sort_values('fecha').groupby(['fecha', 'estado'], as_index=False)[metric_col].sum()
    
    fig = px.line(
        temporal_data,
        x='fecha',
        y=metric_col,
        color='estado',
        title=f"Evolución de {metric_col.replace('_', ' ').title()}",
        markers=True
    )
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, use_container_width=True)


# ============================================
# SECCIÓN 4: ESTADÍSTICAS
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📊 Estadísticas</h3>')

numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
if numeric_cols:
    with st.expander("Ver resumen estadístico"):
        summary = pd.DataFrame({
            "Variable": numeric_cols,
            "Media": [filtered_df[col].mean() for col in numeric_cols],
            "Min": [filtered_df[col].min() for col in numeric_cols],
            "Max": [filtered_df[col].max() for col in numeric_cols]
        }).round(2)
        
        st.dataframe(summary, use_container_width=True)


# ============================================
# SECCIÓN 5: DESCARGAR DATOS
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">💾 Exportar</h3>')

csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
st.download_button(
    label="📥 Descargar CSV",
    data=csv_data,
    file_name=f"covid_{metric_col}_{int(filtered_df['estado'].nunique())}_estados.csv",
    mime="text/csv"
)


# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.caption(
    f"🦠 COVID-19 EDA Dashboard | IA P1-BCN Maestría 2º\n"
    f"*Filtro temporal: {start_date if st.session_state.date_filter else 'Completo'} - {end_date if st.session_state.date_filter else last_date.strftime('%d/%m/%Y')}*"
)