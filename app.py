import pandas as pd
from pathlib import Path
import streamlit as st
import plotly.express as px

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
    first_date = df['fecha'].min().strftime('%d/%m/%Y')
    last_date = df['fecha'].max().strftime('%d/%m/%Y')
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("Registros", len(df))
    with cols[1]:
        st.metric("Estados", df['estado'].nunique())
    with cols[2]:
        total_days = (df['fecha'].max() - df['fecha'].min()).days + 1
        st.metric("Días", total_days)
    with cols[3]:
        st.metric("Rango", f"{first_date} - {last_date}")
    
    st.session_state.initialized = True

# ============================================
# SIDEBAR - CONFIGURACIÓN
# ============================================

with st.sidebar:
    st.header("Configuración")
    
    base_metrics = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales', 'tests_acum']
    other_metrics = [col for col in df.columns if col not in base_metrics and 'acum' not in col.lower()]
    metric_columns = sorted(base_metrics + other_metrics, key=str.lower)
    
    selected_metric = st.selectbox(
        "Métrica a analizar:",
        metric_columns,
        index=0,
        help="Selecciona la métrica que deseas visualizar"
    )
    
    st.session_state.selected_metric = selected_metric
    
    st.divider()
    
    today = pd.Timestamp("today")
    
    date_option = st.radio(
        "Periodo temporal:",
        ["Desde el inicio", "-30 días", "-60 días", "-90 días"],
        horizontal=True
    )
    
    if date_option == "Desde el inicio":
        st.session_state.date_filter = None
        st.info("Mostrar todos los datos disponibles")
    else:
        days_map = {"-30 días": 30, "-60 días": 60, "-90 días": 90}
        days = days_map[date_option]
        start_date = today - pd.Timedelta(days=days)
        end_date = today
        st.session_state.date_filter = (start_date, end_date)
        st.caption(f"📌 {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")

# ============================================
# APLICAR FILTROS
# ============================================

metric_col = st.session_state.selected_metric
filtered_df = df.copy()

if st.session_state.date_filter:
    start_date, end_date = st.session_state.date_filter
    mask = (df['fecha'] >= start_date) & (df['fecha'] <= end_date)
    filtered_df = df.loc[mask].copy()

# ============================================
# SECCIÓN 1: TARJETAS DE MÉTRICAS
# ============================================

st.header("Resumen del Periodo")

if not filtered_df.empty and metric_col in filtered_df.columns:
    total_val = float(filtered_df[metric_col].sum()) if pd.api.types.is_numeric_dtype(filtered_df[metric_col]) else 0
    
    cols = st.columns(4)
    
    with cols[0]:
        display_val = f"{int(round(total_val)):,}" if total_val != 0 else "N/A"
        st.metric(label=f"{metric_col.replace('_', ' ').title()}", value=display_val)
    
    with cols[1]:
        death_sum = float(filtered_df['muertes_acum'].sum()) if 'muertes_acum' in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df['muertes_acum']) else None
        if death_sum is not None:
            st.metric(label="Muertes", value=f"{int(round(death_sum)):,}")
        else:
            st.info("Sin datos de muertes")
    
    with cols[2]:
        hosp_sum = float(filtered_df['hospitalizados_actuales'].sum()) if 'hospitalizados_actuales' in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df['hospitalizados_actuales']) else None
        if hosp_sum is not None:
            st.metric(label="Hospitalizados", value=f"{int(round(hosp_sum)):,}")
        else:
            st.info("Sin datos de hospitalizaciones")
    
    with cols[3]:
        state_count = filtered_df['estado'].nunique()
        st.metric(label="Estados con datos", value=state_count)

# ============================================
# SECCIÓN 1.5: GRÁFICO DE DISTRIBUCIÓN POR ESTADOS
# ============================================

st.header("📊 Top Estados por Impacto", divider="blue")

if not filtered_df.empty and metric_col in filtered_df.columns:
    state_summary = filtered_df.groupby('estado').agg({metric_col: 'sum'}).rename(columns={metric_col: 'Total'})
    
    for col in ['muertes_acum', 'hospitalizados_actuales']:
        if col in filtered_df.columns:
            state_summary[col] = filtered_df.groupby('estado')[col].sum()
    
    state_summary = state_summary.sort_values('Total', ascending=False).head(15)
    
    fig = px.bar(
        state_summary.reset_index(),
        x='estado',
        y='Total',
        orientation='h',
        title=f"Top 15 Estados por {metric_col.replace('_', ' ').title()}",
        color='Total',
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
    fig.update_traces(textposition='outside')
    
    st.plotly_chart(fig, use_container_width=True)

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
    show_limit = min(25, len(state_summary))
    display_df = state_summary.sort_values(metric_col, ascending=False).head(show_limit)
    
    st.dataframe(display_df.round(0), use_container_width=True)

# ============================================
# SECCIÓN 3: COMPARACIÓN DE MÚLTIPLES MÉTRICAS
# ============================================

st.header("Comparación de Métricas", divider="blue")

if not filtered_df.empty:
    base_columns = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales']
    available_metrics = [col for col in base_columns if col in filtered_df.columns]
    
    if len(available_metrics) >= 2:
        sort_column = available_metrics[0]
        compare_data = filtered_df.groupby('estado')[available_metrics].sum().reset_index()
        
        try:
            compare_df = compare_data.sort_values(sort_column, ascending=False).head(20).rename(
                columns={col: col.replace('_', ' ').title() for col in available_metrics}
            )
            st.dataframe(compare_df.round(2), use_container_width=True, height=350)
        except Exception as e:
            st.error(f"Error al mostrar comparación: {str(e)}")

# ============================================
# SECCIÓN 4: GRÁFICO DE CORRELACIÓN ENTRE MÉTRICAS
# ============================================

st.header("🔗 Correlación entre Métricas", divider="blue")

if not filtered_df.empty:
    numeric_cols = [col for col in filtered_df.columns 
                    if col in ['casos_acum', 'muertes_acum', 'hospitalizados_actuales', 'tests_acum']
                    and 'poblacion' not in col.lower()]
    
    if len(numeric_cols) >= 2:
        try:
            correlation_matrix = filtered_df[numeric_cols].corr().round(3)
            
            fig = px.imshow(
                correlation_matrix,
                text_auto='.2f',
                color_continuous_scale='RdBu_r',
                title="Matriz de Correlación entre Métricas",
                aspect='square'
            )
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error al generar matriz de correlación: {str(e)}")

# ============================================
# SECCIÓN 5: TENDENCIAS TEMPORALES (AGREGADAS POR SEMANA)
# ============================================

st.header("📅 Tendencias Temporales", divider="blue")

if not filtered_df.empty and 'fecha' in filtered_df.columns:
    grouped = filtered_df.copy()
    
    try:
        grouped['year_week'] = grouped['fecha'].dt.to_period('W')
        
        if metric_col in filtered_df.columns and 'year_week' in grouped.columns:
            weekly_trend = grouped.groupby(['year_week', 'estado'])[metric_col].sum().reset_index()
            
            # Top 5 estados sin usar default=None (no existe en Python 3.14)
            top_states_sorted = weekly_trend.groupby('estado')[metric_col].sum().sort_values(ascending=False).head(5)
            top_states = top_states_sorted.index.tolist()
            
            if len(top_states) > 0 and metric_col in grouped.columns:
                fig = px.line(
                    weekly_trend[weekly_trend['estado'].isin(top_states)],
                    x='year_week',
                    y=metric_col,
                    color='estado',
                    title=f"Tendencia Semanal de {metric_col.replace('_', ' ').title()} (Top 5 Estados)",
                    markers=True,
                    hover_data=['estado']
                )
                
                fig.update_layout(height=400)
                fig.update_xaxes(tickformat='%d/%m')
                
                st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("No se pudo agregar la columna de semanas (posible problema con fechas)")

# ============================================
# SECCIÓN 6: GRÁFICO DE DISTRIBUCIÓN POR REGION
# ============================================

st.header("🗺️ Distribución por Región", divider="blue")

if not filtered_df.empty and 'region' in filtered_df.columns:
    regional_summary = filtered_df.groupby('region').agg({metric_col: 'sum'}).rename(
        columns={metric_col: 'Total'}
    )
    
    for col in ['muertes_acum', 'hospitalizados_actuales']:
        if col in filtered_df.columns:
            regional_summary[col] = filtered_df.groupby('region')[col].sum()
    
    try:
        regional_summary = regional_summary.sort_values('Total', ascending=False).head(10)
        
        fig = px.treemap(
            regional_summary.reset_index(),
            path=['region'],
            values='Total',
            title=f"Distribución por Región ({metric_col.replace('_', ' ').title()})",
            color='Total',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=500)
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error al generar gráfico de región: {str(e)}")

# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.caption(
    "COVID-19 EDA Dashboard | IA P1-BCN Maestría 2º\n\n"
    f"Métrica: {metric_col.replace('_', ' ').title()}\n\n"
    f"Filtro temporal aplicado"
)