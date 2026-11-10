import pandas as pd
from pathlib import Path
import streamlit as st

# Configuración
st.set_page_config(
    page_title="COVID-19 EDA Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CARGA DE DATOS - SIN CACHE PARA FORZAR RECARGA
# ============================================

def load_data():
    """Carga los datos procesados."""
    script_dir = Path(__file__).parent
    csv_path = script_dir / "data" / "processed" / "covid_estados_final.csv"
    df = pd.read_csv(csv_path)
    df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
    return df

# ============================================
# CARGA Y MENSAJE DE INICIO
# ============================================

df = load_data()

with st.expander("📦 Información de carga"):
    st.success(f"✅ Cargados {len(df):,} registros de {df['estado'].nunique()} estados")
    
    first_date = df['fecha'].min().strftime('%d/%m/%Y')
    last_date = df['fecha'].max().strftime('%d/%m/%Y')
    st.info(f"📅 Rango de datos: {first_date} a {last_date}")

# ============================================
# SIDEBAR - FILTROS
# ============================================

with st.sidebar:
    st.header("⚙️ Configuración", divider="primary")
    
    # Columnas disponibles
    metric_columns = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales'] + \
                     [col for col in df.columns if col not in ['casos_acum', 'muertes_acum', 'hospitalizados_actuales']]
    
    selected_metric = st.selectbox(
        "📊 Métrica a analizar:",
        sorted(metric_columns, key=str.lower),
        index=0,  # Por defecto casos_acum
    )
    
    st.session_state.selected_metric = selected_metric
    
    st.divider()
    
    # Filtros temporales
    last_date_ts = df['fecha'].max()
    
    date_option = st.radio(
        "📅 Período temporal:",
        ["Completo", "-30 días", "-60 días", "-90 días"],
        horizontal=True,
        key="date_filter"  # Clave única
    )
    
    if date_option == "Completo":
        st.session_state.date_filter = None
        st.info("✅ Mostrar todos los datos")
    else:
        days_map = {"-30 días": 30, "-60 días": 60, "-90 días": 90}
        days = days_map[date_option]
        
        # Usar última fecha del dataset como referencia (NO hoy!)
        end_date = last_date_ts.date()
        start_date = (last_date_ts - pd.Timedelta(days=days)).date()
        
        st.session_state.date_filter = (start_date, end_date)
        st.caption(f"📌 {start_date} a {end_date}")

# ============================================
# APLICAR FILTROS
# ============================================

metric_col = st.session_state.selected_metric
filtered_df = df.copy()

if st.session_state.date_filter:
    start_date, end_date = st.session_state.date_filter
    mask = (df['fecha'] >= pd.Timestamp(start_date)) & (df['fecha'] <= pd.Timestamp(end_date))
    filtered_df = df.loc[mask].copy()
    
    # Contar estados con datos
    if metric_col in filtered_df.columns:
        states_with_data = filtered_df['estado'].nunique()
        total_states = df['estado'].nunique()
        
        if date_option != "Completo" and states_with_data < 50 and 'acum' in metric_col.lower():
            st.warning(
                f"⚠️ Filtro temporal: Solo {states_with_data} de {total_states} estados tienen datos\n"
                f"En periodos cortos, los datos acumulativos solo están disponibles para algunos estados."
            )

# ============================================
# SECCIÓN 1: TARJETAS DE MÉTRICAS (SIMPLES Y ROBUSTAS)
# ============================================

st.header("📊 Resumen del Período", divider="blue")

if not filtered_df.empty and metric_col in filtered_df.columns:
    total = float(filtered_df[metric_col].sum())
    
    # Obtener otras métricas de forma segura
    death_total = None
    hosp_total = None
    fatality_rate = None
    
    if 'muertes_acum' in filtered_df.columns:
        death_total = float(filtered_df['muertes_acum'].sum())
        fatality_rate = (death_total / total * 100) if total > 0 else 0.0
    
    if 'hospitalizados_actuales' in filtered_df.columns:
        hosp_total = float(filtered_df['hospitalizados_actuales'].sum())
    
    # Columnas para cards
    cols = st.columns(4)
    
    # Card 1: Métrica principal
    with cols[0]:
        display_val = f"{int(round(total)):,}" if not pd.isna(total) else "N/A"
        delta_text = ""
        
        if fatality_rate is not None and death_total is not None and not pd.isna(death_total):
            st.metric(
                label=f"📋 {metric_col.replace('_', ' ').title()}",
                value=display_val,
                delta=f"{fatality_rate:.2f}%",
                delta_color="normal"
            )
        else:
            st.metric(label=f"📋 {metric_col.replace('_', ' ').title()}", value=display_val)
    
    # Card 2: Muertes (si existe)
    with cols[1]:
        if death_total is not None and not pd.isna(death_total):
            st.metric(
                label="⚰️ Muertes",
                value=f"{int(round(death_total)):,}",
                delta=f"{fatality_rate:.2f}%"
            )
        else:
            st.info("ℹ️ No hay datos de muertes")
    
    # Card 3: Hospitalizados (si existe)
    with cols[2]:
        if hosp_total is not None and not pd.isna(hosp_total):
            st.metric(label="🏥 Hospitalizados", value=f"{int(round(hosp_total)):,}")
        else:
            st.info("ℹ️ No hay datos de hospitalizaciones")
    
    # Card 4: Población (si existe)
    with cols[3]:
        if 'poblacion' in filtered_df.columns and filtered_df['poblacion'].sum() > 0:
            pop_total = float(filtered_df['poblacion'].sum())
            per_capita = total / pop_total
            st.metric(
                label="👥 Casos por Habitante",
                value=f"{per_capita:.2f}"
            )
        else:
            st.info("ℹ️ No hay datos de población")


# ============================================
# SECCIÓN 2: DATOS POR ESTADO (TABLA INTERACTIVA)
# ============================================

st.header("🗺️ Datos por Estado", divider="blue")

if not filtered_df.empty and metric_col in filtered_df.columns:
    
    # Agrupar por estado y sumar métricas principales
    state_summary = filtered_df.groupby('estado').agg({
        metric_col: 'sum'
    })
    
    # Agregar otras métricas si existen
    for col in ['muertes_acum', 'hospitalizados_actuales', 'tests_acum']:
        if col in filtered_df.columns:
            state_summary[col] = filtered_df.groupby('estado')[col].sum()
    
    # Convertir índice a columna para mejor display
    state_summary.index.name = None
    
    # Ordenar por métrica principal
    state_summary = state_summary.sort_values(metric_col, ascending=False)
    
    # Tomar top 30 estados
    top_states = state_summary.head(30).copy()
    
    st.dataframe(
        top_states.style.format('{:.0f}').applymap(
            lambda v: '<font color="red">' + str(v) + '</font>' if pd.isna(v) or v == 0 else str(v),
            subset=[]
        ),
        use_container_width=True,
        height=500
    )


# ============================================
# SECCIÓN 3: COMPARACIÓN DE MÚLTIPLES MÉTRICAS
# ============================================

st.header("🔍 Comparación de Métricas", divider="blue")

if not filtered_df.empty and metric_col in filtered_df.columns:
    
    # Verificar qué métricas principales existen
    base_columns = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales']
    available_metrics = [col for col in base_columns if col in filtered_df.columns]
    
    if len(available_metrics) > 1:
        # Crear tabla comparativa
        compare_df = filtered_df.groupby('estado')[available_metrics].sum().reset_index()
        
        # Tomar top 20 estados
        compare_df = compare_df.sort_values(metric_col, ascending=False).head(20)
        
        # Renombrar columnas para display
        col_names = {}
        for col in available_metrics:
            col_names[col] = col.replace('_', ' ').title()
        
        compare_df.rename(columns=col_names, inplace=True)
        
        st.dataframe(
            compare_df.style.format('{:.0f}').applymap(
                lambda v: '' if pd.isna(v) else str(v),
                subset=[]
            ),
            use_container_width=True,
            height=400
        )


# ============================================
# SECCIÓN 4: ESTADÍSTICAS RESUMEN
# ============================================

st.header("📊 Estadísticas", divider="blue")

if not filtered_df.empty:
    numeric_cols = [col for col in filtered_df.select_dtypes(include=['number']).columns]
    
    if numeric_cols:
        with st.expander("Ver resumen estadístico"):
            summary = pd.DataFrame({
                "Métrica": numeric_cols,
                "Media": [filtered_df[col].mean() for col in numeric_cols],
                "Total": [filtered_df[col].sum() for col in numeric_cols]
            })
            
            # Redondear valores
            summary["Media"] = summary["Media"].round(2)
            summary["Total"] = summary["Total"].round(0).apply(lambda x: '' if pd.isna(x) else f"{int(round(x)):,}")
            
            st.dataframe(summary, use_container_width=True)


# ============================================
# SECCIÓN 5: INFO DE FILTROS
# ============================================

st.header("📅 Filtros Activos", divider="blue")

if st.session_state.date_filter:
    start_date, end_date = st.session_state.date_filter
    st.info(f"✅ Mostrando datos de **{start_date}** a **{end_date}** (relativo al último dato disponible del dataset)")
else:
    first_date = df['fecha'].min()
    last_date = df['fecha'].max()
    st.info(f"✅ Mostrando TODOS los datos desde **{first_date.strftime('%d/%m/%Y')}** hasta **{last_date.strftime('%d/%m/%Y')}**")

# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.caption(
    f"🦠 COVID-19 EDA Dashboard | IA P1-BCN Maestría 2º\n\n"
    f"*Métrica: {metric_col.replace('_', ' ').title()}*\n"
    f*"Registros cargados: {len(df):,} | Estados: {df['estado'].nunique()}*"
)