import pandas as pd
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go

# Configuración
st.set_page_config(
    page_title="COVID-19 EDA Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CARGA DE DATOS
# ============================================

@st.cache_data(ttl=None)
def load_data():
    """Carga los datos procesados."""
    script_dir = Path(__file__).parent
    csv_path = script_dir / "data" / "processed" / "covid_estados_final.csv"
    df = pd.read_csv(csv_path)
    df['fecha'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_localize(None)
    return df

# ============================================
# CARGA E INICIALIZACIÓN
# ============================================

df = load_data()

# Inicializar session state una sola vez
if "initialized" not in st.session_state:
    st.success(f"✅ Cargados {len(df)} registros de {df['estado'].nunique()} estados")
    
    # Estadísticas rápidas
    cols = st.columns(4)
    with cols[0]:
        st.metric("Registros", len(df))
    with cols[1]:
        st.metric("Estados", df['estado'].nunique())
    with cols[2]:
        first_date = df['fecha'].min().strftime('%d/%m/%Y')
        last_date = df['fecha'].max().strftime('%d/%m/%Y')
        st.metric("Rango Fecha", f"{first_date} - {last_date}")
    
    st.session_state.initialized = True

# ============================================
# SIDEBAR - FILTROS
# ============================================

with st.sidebar:
    st.header("⚙️ Configuración", divider="primary")
    
    # Columnas disponibles (agregamos columna derivada para casos no acum)
    metric_columns = [
        'casos_acum',
        'muertes_acum', 
        'hospitalizados_actuales',
        'tests_acum'
    ]
    
    # Verificar columnas adicionales del dataframe
    for col in df.columns:
        if col not in metric_columns and 'acum' not in col.lower() and 'poblacion' in col.lower():
            metric_columns.append(col)
    
    selected_metric = st.selectbox(
        "📊 Métrica a analizar:",
        sorted(metric_columns, key=str.lower),
        index=0,  # Por defecto casos_acum
        help="Selecciona la métrica que deseas visualizar"
    )
    
    st.session_state.selected_metric = selected_metric
    
    st.divider()
    
    # Filtros temporales - CRÍTICO: Usar fecha max del dataset
    last_date = df['fecha'].max()
    first_date = df['fecha'].min()
    
    date_option = st.radio(
        "📅 Período temporal:",
        ["Completo", "-30 días", "-60 días", "-90 días"],
        horizontal=True,
        key="temporal_filter"  # Clave única para recalcular siempre
    )
    
    if date_option == "Completo":
        st.session_state.date_filter = None
    else:
        days_map = {"-30 días": 30, "-60 días": 60, "-90 días": 90}
        days = days_map[date_option]
        
        # 🔴 CORRECCIÓN: Usar última fecha del dataset como referencia
        end_date = last_date.date()
        start_date = (last_date - pd.Timedelta(days=days)).date()
        
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
    
    # Contar cuántos estados tienen datos en este rango
    states_with_data = df.loc[mask, 'estado'].nunique()
    total_states = df['estado'].nunique()
    
    if metric_col in df.columns:
        filtered_df = df.loc[mask].copy()
        
        # Mostrar advertencia si hay pocos estados con datos
        if states_with_data < total_states * 0.3 and 'acum' in metric_col.lower():
            st.warning(f"⚠️ Solo {states_with_data}/{total_states} estados tienen datos en este periodo")

# ============================================
# SECCIÓN 1: MÉTRICAS CLAVE (VISUALIZACIÓN INTERACTIVA)
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📈 Métricas Clave</h3>', unsafe_allow_html=True)

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
    
    # Columnas para métricas adicionales
    additional_metrics = {
        col: float(filtered_df[col].sum()) 
        for col in ['tests_acum', 'positividad_7d'] 
        if col in filtered_df.columns and not pd.isna(filtered_df[col].mean())
    }
    
    # Mostrar en cards interactivas
    cols = st.columns(4)
    
    with cols[0]:
        card_label = metric_col.replace('_', ' ').title()
        display_total = f"{int(round(total)):,}" if not pd.isna(total) else "N/A"
        
        if fatality_rate is not None and death_total is not None:
            st.metric(
                label=card_label,
                label=f"{display_total}",
                delta=f"{fatality_rate:.2f}%",
                help=f"Métrica seleccionada\nTotal: {display_total}\nLetalidad: {fatality_rate:.2f}%"
            )
        elif pd.isna(total):
            st.metric(label=card_label, label="N/A", delta=None)
        else:
            st.metric(label=card_label, label=f"{int(round(total)):,}", delta=None)
    
    with cols[1]:
        if death_total is not None and not pd.isna(death_total):
            st.metric(
                label="Muertes Totales",
                label=f"{int(round(death_total)):,}",
                delta=f"{fatality_rate:.2f}%",
                help="Total acumulado de muertes"
            )
        else:
            st.info("ℹ️ Sin datos de muertes")
    
    with cols[2]:
        if hosp_total is not None and not pd.isna(hosp_total):
            st.metric(label="Hospitalizados", label=f"{int(round(hosp_total)):,}")
        elif 'hospitalizados_actuales' not in filtered_df.columns:
            st.info("ℹ️ Sin datos de hospitalizaciones")
    
    with cols[3]:
        # Mostrar métrica adicional
        metric_labels = {
            'tests_acum': ('Pruebas Totales', 'Tests Totales'),
            'positividad_7d': ('Positividad 7d', 'Tasa Positividad')
        }
        
        display_metric, display_label = metric_labels.get(metric_col, (None, metric_col))
        
        if display_metric is not None and not pd.isna(display_metric):
            st.metric(label=display_label, label=f"{int(round(display_metric)):,}")
        elif display_metric is None:
            # Mostrar última métrica disponible
            for col_name in ['tests_acum']:
                if col_name in additional_metrics and col_name != metric_col:
                    st.metric(label=additional_metrics[col_name].replace('_', ' ').title(), label=f"{int(round(additional_metrics[col_name])):,}")
                    break


# ============================================
# SECCIÓN 2: VISUALIZACIÓN POR ESTADOS (TOP 15)
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">🗺️ Top Estados</h3>', unsafe_allow_html=True)

if metric_col in filtered_df.columns and 'estado' in filtered_df.columns:
    state_data = filtered_df.groupby('estado')[metric_col].sum().sort_values(ascending=False).head(15)
    
    # Verificar que hay datos
    if len(state_data) > 0 and not all(pd.isna(state_data.iloc[0, -1]) for _ in range(len(state_data))):
        fig = go.Figure(go.Bar(
            x=state_data.index.astype(str),
            y=state_data.values,
            orientation='h',
            marker_color='blue'
        ))
        
        fig.update_layout(
            title=f"Top 15 Estados por {metric_col.replace('_', ' ').title()}",
            height=400,
            yaxis=dict(title=metric_col.replace('_', ''))
        )
        
        st.plotly_chart(fig, use_container_width=True)


# ============================================
# SECCIÓN 3: DATASET INTERACTIVO COMPARATIVO
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">🔍 Comparar Métricas</h3>', unsafe_allow_html=True)

# Agregar columna con suma de todas las métricas principales
if metric_col in filtered_df.columns:
    base_columns = ['casos_acum', 'muertes_acum', 'hospitalizados_actuales']
    
    # Crear columna combinada si existen todas las métricas principales
    combined_cols = [col for col in base_columns if col in filtered_df.columns]
    
    if len(combined_cols) > 1:
        combined_name = '_COMBINADO'
        filtered_df[combined_name] = filtered_df[combined_cols].sum(axis=1)
        
        # Mostrar tabla interactiva con todas las métricas principales
        st.markdown("**📊 Datos por Estado (Top 20)**")
        
        top_states = filtered_df.groupby('estado')[metric_col].sum().nlargest(20, default=None).reset_index()
        
        if not top_states.empty:
            # Preparar datos para tabla
            display_df = top_states.copy()
            
            for col in ['muertes_acum', 'hospitalizados_actuales', 'tests_acum']:
                if col in filtered_df.columns and col not in ['casos_acum']:
                    display_df[col] = filtered_df.loc[display_df['estado'], col].sum()
            
            st.dataframe(display_df.head(20), use_container_width=True)


# ============================================
# SECCIÓN 4: TENDENCIAS TEMPORALES
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📅 Evolución Temporal</h3>', unsafe_allow_html=True)

if metric_col in filtered_df.columns and 'fecha' in filtered_df.columns:
    temporal_data = filtered_df.sort_values('fecha').groupby(['fecha', 'estado'], as_index=False)[metric_col].sum()
    
    fig = go.Scatter(
        x=temporal_data['fecha'],
        y=temporal_data[metric_col],
        mode='lines+markers',
        name=metric_col.replace('_', '').title(),
        line=dict(width=2)
    )
    
    # Agregar líneas para cada estado en el top 5
    top_states = temporal_data.nlargest(5, metric_col)['estado'].tolist()
    
    for estado in top_states:
        estado_data = temporal_data[temporal_data['estado'] == estado]
        fig.add_trace(go.Scatter(
            x=estado_data['fecha'],
            y=estado_data[metric_col],
            mode='lines',
            name=f'{estado} ({estado_data[metric_col].sum():.0f})'[:20],
            line=dict(width=1, dash='dash')
        ))
    
    fig.update_layout(
        title=f"Evolución de {metric_col.replace('_', ' ').title()} por Estado",
        xaxis_title="Fecha",
        yaxis_title=metric_col.replace('_', ''),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ============================================
# SECCIÓN 5: ESTADÍSTICAS RESUMEN
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">📊 Estadísticas</h3>', unsafe_allow_html=True)

numeric_cols = [col for col in filtered_df.select_dtypes(include=['number']).columns if 'acum' in col.lower() or 'poblacion' in col.lower()]

if numeric_cols:
    with st.expander("Ver resumen estadístico"):
        summary = pd.DataFrame({
            "Métrica": numeric_cols,
            "Media": [filtered_df[col].mean() for col in numeric_cols],
            "Total": [filtered_df[col].sum() for col in numeric_cols]
        })
        
        # Redondear valores muy pequeños
        summary = summary.replace([0.0, float('nan')], None)
        summary["Media"] = summary["Media"].round(4)
        summary["Total"] = summary["Total"].round(2)
        
        st.dataframe(summary, use_container_width=True)


# ============================================
# SECCIÓN 6: DESCARGAR DATOS
# ============================================

st.markdown('<h3 style="margin-top:2rem; color:#1f77b4;">💾 Exportar Datos</h3>', unsafe_allow_html=True)

csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')

st.download_button(
    label="📥 Descargar CSV",
    data=csv_data,
    file_name=f"covid_{metric_col.replace('_', '_')}_{int(filtered_df['estado'].nunique())}_estados.csv" if not filtered_df.empty else "covid_datos.csv",
    mime="text/csv"
)


# ============================================
# FOOTER
# ============================================

st.markdown("---")
start_date_str = start_date if st.session_state.date_filter else first_date.strftime('%d/%m/%Y')
end_date_str = end_date if st.session_state.date_filter else last_date.strftime('%d/%m/%Y')

st.caption(
    f"🦠 COVID-19 EDA Dashboard | IA P1-BCN Maestría 2º\n"
    f"*Filtro temporal: {start_date_str} - {end_date_str}*\n"
    f*Métrica seleccionada: {metric_col.replace('_', ' ').title()}*"
)