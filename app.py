import pandas as pd
from pathlib import Path
import streamlit as st

# Configuración
st.set_page_config(
    page_title="COVID-19 EDA Dashboard",
    layout="wide"
)

# ============================================
# CARGA DE DATOS
# ============================================

@st.cache_data(ttl=None)
def load_data():
    script_dir = Path(__file__).parent
    csv_path = script_dir / "data" / "processed" / "covid_estados_final.csv"
    df = pd.read_csv(csv_path)
    df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
    return df

df = load_data()

# ============================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================

if "initialized" not in st.session_state:
    st.success(f"Cargados {len(df):,} registros de {df['estado'].nunique()} estados")
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("Registros", len(df))
    with cols[1]:
        st.metric("Estados", df['estado'].nunique())
    with cols[2]:
        total_days = (df['fecha'].max() - df['fecha'].min()).days + 1
        st.metric("Días", total_days)
    with cols[3]:
        first_date = df['fecha'].min().strftime('%d/%m/%Y')
        last_date = df['fecha'].max().strftime('%d/%m/%Y')
        st.metric("Rango", f"{first_date} - {last_date}")
    
    st.session_state.initialized = True

# ============================================
# SIDEBAR - CONFIGURACIÓN
# ============================================

with st.sidebar:
    st.header("Configuración")
    
    # Definir columnas disponibles para el selector de métricas
    base_metrics = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales', 'tests_acum']
    other_metrics = [col for col in df.columns if col not in base_metrics and 'acum' not in col.lower()]
    metric_columns = base_metrics + other_metrics
    
    selected_metric = st.selectbox(
        "Métrica a analizar:",
        sorted(metric_columns, key=str.lower),
        index=0,
        help="Selecciona la métrica que deseas visualizar"
    )
    
    st.session_state.selected_metric = selected_metric
    
    st.divider()
    
    # Inicializar filtros temporales con fecha máxima del dataset
    last_date_ts = df['fecha'].max()
    
    date_option = st.radio(
        "Periodo temporal:",
        ["Completo", "-30 días", "-60 días", "-90 días"],
        horizontal=True
    )
    
    # Setear filtros según selección del usuario
    if date_option == "Completo":
        st.session_state.date_filter = None
        st.info("Mostrar todos los datos")
    else:
        days_map = {"-30 días": 30, "-60 días": 60, "-90 días": 90}
        days = days_map[date_option]
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

# ============================================
# SECCIÓN 1: TARJETAS DE MÉTRICAS
# ============================================

st.header("Resumen del Periodo")

if not filtered_df.empty and metric_col in filtered_df.columns:
    total = float(filtered_df[metric_col].sum())
    
    death_total = None
    hosp_total = None
    
    if 'muertes_acum' in filtered_df.columns:
        death_total = float(filtered_df['muertes_acum'].sum())
    
    if 'hospitalizados_actuales' in filtered_df.columns:
        hosp_total = float(filtered_df['hospitalizados_actuales'].sum())
    
    cols = st.columns(4)
    
    with cols[0]:
        display_val = f"{int(round(total)):,}" if not pd.isna(total) else "N/A"
        if death_total is not None and not pd.isna(death_total):
            st.metric(label=f"{metric_col.replace('_', ' ').title()}", value=display_val, delta=f"{(death_total/total*100):.2f}%" if total > 0 else "0.00%")
        else:
            st.metric(label=f"{metric_col.replace('_', ' ').title()}", value=display_val)
    
    with cols[1]:
        if death_total is not None and not pd.isna(death_total):
            st.metric(label="Muertes", value=f"{int(round(death_total)):,}")
        else:
            st.info("Sin datos de muertes")
    
    with cols[2]:
        if hosp_total is not None and not pd.isna(hosp_total):
            st.metric(label="Hospitalizados", value=f"{int(round(hosp_total)):,}")
        else:
            st.info("Sin datos de hospitalizaciones")

# ============================================
# SECCIÓN 2: TABLA POR ESTADO
# ============================================

st.header("Datos por Estado")

if not filtered_df.empty and metric_col in filtered_df.columns:
    state_summary = filtered_df.groupby('estado').agg({metric_col: 'sum'})
    
    for col in ['muertes_acum', 'hospitalizados_actuales']:
        if col in filtered_df.columns:
            state_summary[col] = filtered_df.groupby('estado')[col].sum()
    
    state_summary.index.name = None
    state_summary = state_summary.sort_values(metric_col, ascending=False).head(25)
    
    st.dataframe(state_summary.round(0), use_container_width=True)

# ============================================
# SECCIÓN 3: COMPARACIÓN DE MÚLTIPLES MÉTRICAS
# ============================================

st.header("Comparación de Métricas")

if not filtered_df.empty and metric_col in filtered_df.columns:
    base_columns = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales']
    available_metrics = [col for col in base_columns if col in filtered_df.columns]
    
    if len(available_metrics) > 1:
        metric_sort_column = metric_col
    compare_data = filtered_df.groupby('estado')[available_metrics].sum().reset_index()
    
    # Ordenar por métrica original y limitar a top 20
    if metric_sort_column in compare_data.columns:
        compare_df = compare_data.sort_values(metric_sort_column, ascending=False).head(20).rename(
            columns={col: col.replace('_', ' ').title() for col in available_metrics}
        )
        st.dataframe(compare_df.round(0), use_container_width=True)

# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.caption(
    "COVID-19 EDA Dashboard\n\n"
    f"Métrica: {metric_col.replace('_', ' ').title()}\n\n"
    f"Filtro temporal aplicado"
)