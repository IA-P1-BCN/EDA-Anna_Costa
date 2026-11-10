import pandas as pd
from pathlib import Path
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="COVID-19 EDA Dashboard", layout="wide")

@st.cache_data(ttl=None)
def load_data():
    csv_path = Path(__file__).parent / "data" / "processed" / "covid_estados_final.csv"
    df = pd.read_csv(csv_path)
    df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
    return df

df = load_data()

if "initialized" not in st.session_state:
    first_date = df['fecha'].min().strftime('%d/%m/%Y')
    last_date = df['fecha'].max().strftime('%d/%m/%Y')
    
    cols = st.columns(4)
    with cols[0]: st.metric("Registros", len(df))
    with cols[1]: st.metric("Estados", df['estado'].nunique())
    with cols[2]: st.metric("Días", (df['fecha'].max() - df['fecha'].min()).days + 1)
    with cols[3]: st.metric("Rango", f"{first_date} - {last_date}")
    
    st.success(f"✓ Cargados {len(df):,} registros")
    st.session_state.initialized = True

with st.sidebar:
    st.header("Configuración")
    
    base_metrics = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales', 'tests_acum']
    other_metrics = [col for col in df.columns if col not in base_metrics and 'acum' not in col.lower()]
    metric_columns = sorted(base_metrics + other_metrics, key=str.lower)
    
    selected_metric = st.selectbox("Métrica a analizar:", metric_columns, index=0)
    st.session_state.selected_metric = selected_metric
    
    st.divider()
    
    today = pd.Timestamp("today")
    
    date_option = st.radio("Periodo temporal:", ["Desde el inicio", "-30 días", "-60 días", "-90 días"], horizontal=True)
    
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

metric_col = st.session_state.selected_metric
filtered_df = df.copy()

if st.session_state.date_filter:
    start_date, end_date = st.session_state.date_filter
    mask = (df['fecha'] >= start_date) & (df['fecha'] <= end_date)
    filtered_df = df.loc[mask].copy()
    st.caption(f"📊 Filtrado: {len(filtered_df):,} registros después del filtro temporal")

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
        if death_sum is not None: st.metric(label="Muertes", value=f"{int(round(death_sum)):,}")
        else: st.info("Sin datos de muertes")
    
    with cols[2]:
        hosp_sum = float(filtered_df['hospitalizados_actuales'].sum()) if 'hospitalizados_actuales' in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df['hospitalizados_actuales']) else None
        if hosp_sum is not None: st.metric(label="Hospitalizados", value=f"{int(round(hosp_sum)):,}")
        else: st.info("Sin datos de hospitalizaciones")
    
    with cols[3]:
        state_count = filtered_df['estado'].nunique()
        st.metric(label="Estados con datos", value=state_count)

# ============================================
# SECCIÓN 2: GRÁFICO DE BARRAS HORIZONTALES CORREGIDO
# ============================================

st.header("📊 Top Estados por Impacto", divider="blue")

if not filtered_df.empty and metric_col in filtered_df.columns:
    # Agrupar y sumar por estado - USAR RESET_INDEX CORRECTAMENTE
    state_summary = filtered_df.groupby('estado')[metric_col].sum().reset_index()
    
    if len(state_summary) > 0 and pd.api.types.is_numeric_dtype(state_summary[metric_col]):
        # Filtrar NaN si existen
        state_summary_clean = state_summary.dropna(subset=[metric_col])
        
        if len(state_summary_clean) > 0:
            top_15 = state_summary_clean.head(15)
            
            # Crear gráfico de barras horizontales con sintaxis correcta
            fig = px.bar(top_15, x=metric_col, y='estado', orientation='h',
                         title=f"Top 15 Estados por {metric_col.replace('_', ' ').title()}",
                         color=metric_col, color_continuous_scale='Blues')
            fig.update_layout(height=400)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Los datos de {metric_col} son todos NaN después del filtro temporal")
    else:
        st.warning(f"No hay valores numéricos para {metric_col}")
else:
    st.warning(f"Métrica {metric_col} no disponible en el dataset")

# ============================================
# SECCIÓN 3: TABLA POR ESTADO
# ============================================

st.header("Datos por Estado", divider="blue")

if not filtered_df.empty and metric_col in filtered_df.columns:
    state_summary = filtered_df.groupby('estado')[metric_col].sum()
    
    # Filtrar NaN y ordenar
    state_summary_clean = state_summary.dropna().sort_values(ascending=False)
    
    if len(state_summary_clean) > 0:
        show_limit = min(25, len(state_summary_clean))
        display_df = state_summary_clean.head(show_limit).to_frame(name=metric_col).reset_index()
        
        st.dataframe(display_df.round(0), use_container_width=True)
    else:
        st.warning(f"No hay datos válidos para {metric_col}")

# ============================================
# SECCIÓN 4: COMPARACIÓN DE MÚLTIPLES MÉTRICAS
# ============================================

st.header("Comparación de Métricas", divider="blue")

if not filtered_df.empty:
    base_columns = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales']
    available_metrics = [col for col in base_columns if col in filtered_df.columns]
    
    if len(available_metrics) >= 2:
        # Crear dataframe de comparación correctamente
        compare_data_list = []
        
        for col in available_metrics:
            values = filtered_df[col].dropna()
            if len(values) > 0:
                compare_df = filtered_df.groupby('estado')[col].sum().reset_index()
                compare_data_list.append(compare_df)
        
        if len(compare_data_list) >= 2:
            # Fusionar todos los dataframes
            first_df = compare_data_list[0]
            for df in compare_data_list[1:]:
                first_df = first_df.merge(df, on='estado', how='outer')
            
            # Renombrar columnas
            renamed_cols = {i+1: name.title().replace('_', ' ') for i, name in enumerate(available_metrics)}
            first_df = first_df.rename(columns={col: name for col, name in zip(available_metrics, [name.title().replace('_', ' ') for name in available_metrics])})
            
            # Ordenar y limitar a top 20
            first_df = first_df.sort_values(available_metrics[0], ascending=False).head(20)
            
            st.dataframe(first_df.round(2), use_container_width=True, height=350)

# ============================================
# SECCIÓN 5: MATRIZ DE CORRELACIÓN
# ============================================

st.header("🔗 Correlación entre Métricas", divider="blue")

if not filtered_df.empty:
    numeric_cols = [col for col in filtered_df.columns 
                    if col in ['casos_acum', 'muertes_acum', 'hospitalizados_actuales', 'tests_acum']
                    and 'poblacion' not in col.lower()]
    
    if len(numeric_cols) >= 2:
        try:
            correlation_matrix = filtered_df[numeric_cols].corr().round(3)
            
            fig = px.imshow(correlation_matrix, text_auto='.2f', color_continuous_scale='RdBu_r',
                           title="Matriz de Correlación entre Métricas", aspect='square')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error al generar matriz de correlación: {str(e)}")

# ============================================
# SECCIÓN 6: TENDENCIAS TEMPORALES
# ============================================

st.header("📅 Tendencias Temporales", divider="blue")

if not filtered_df.empty and 'fecha' in filtered_df.columns:
    try:
        grouped = filtered_df.copy()
        
        if metric_col in filtered_df.columns:
            # Verificar que la métrica tiene datos válidos
            valid_values = filtered_df[metric_col].dropna()
            
            if len(valid_values) > 0:
                # Usar formato string para evitar problemas con fechas futuras
                grouped['year_week'] = grouped['fecha'].dt.strftime('%Y-W%W')
                
                weekly_trend = grouped.groupby(['year_week', 'estado'])[metric_col].sum().reset_index()
                
                if len(weekly_trend) > 0:
                    # Top 5 estados por métrica seleccionada
                    top_5_by_metric = filtered_df.groupby('estado')[metric_col].sum().nlargest(5).index.tolist()
                    
                    if len(top_5_by_metric) > 0:
                        fig_weekly = px.line(weekly_trend, x='year_week', y=metric_col,
                                            title=f"Tendencia Semanal de {metric_col.replace('_', ' ').title()}",
                                            color='estado', markers=True, hover_data=['estado'])
                        fig_weekly.update_layout(height=400)
                        
                        st.plotly_chart(fig_weekly, use_container_width=True)
                    else:
                        st.info("No hay suficientes datos para mostrar tendencias por estado")
                else:
                    st.warning("No hay semanas generadas a partir de las fechas")
            else:
                st.warning(f"La métrica {metric_col} no tiene valores válidos para gráficos temporales")
        else:
            st.warning(f"Métrica {metric_col} no disponible en el dataset")
    except Exception as e:
        st.error(f"Error al generar gráfico temporal: {str(e)}")

# ============================================
# SECCIÓN 7: GRÁFICO DE REGIONES
# ============================================

st.header("🗺️ Distribución por Región", divider="blue")

if not filtered_df.empty and 'region' in filtered_df.columns:
    regional_summary = filtered_df.groupby('region')[metric_col].sum()
    
    if len(regional_summary) > 0 and pd.api.types.is_numeric_dtype(regional_summary):
        regional_clean = regional_summary.dropna().sort_values(ascending=False).head(10)
        
        if len(regional_clean) > 0:
            fig = px.treemap(regional_clean.reset_index(), path=['region'], values=metric_col,
                            title=f"Distribución por Región ({metric_col.replace('_', ' ').title()})",
                            color=metric_col, color_continuous_scale='Greens')
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No hay datos válidos por región para {metric_col}")
    else:
        st.warning(f"La columna 'region' no tiene valores numéricos válidos")
else:
    st.info("La columna 'region' no está disponible en el dataset")

st.markdown("---")
st.caption("COVID-19 EDA Dashboard | IA P1-BCN Maestría 2º\n\n"
           f"Métrica seleccionada: {metric_col.replace('_', ' ').title()}\n\n"
           "Filtro temporal aplicado")