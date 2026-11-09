"""📊 COVID-19 Dashboard - Estados Unidos (2020-2021)
Optimizado para despliegue en Streamlit Cloud

Este dashboard interactivo visualiza los datos de COVID-19 procesados desde The COVID Tracking Project.

🌐 Fuentes de datos:
   - The COVID Tracking Project (casos, muertes, hospitalizados)
   - US Census Bureau (población por estado)
   
📚 Licencia: CC BY 4.0
   
ℹ️ Para ejecutar localmente (requiere entorno virtual):
   streamlit run app.py

🌐 Para desplegar en Streamlit Cloud:
   Sube este repositorio a GitHub (brama main) y conecta en https://streamlit.io/cloud
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================

st.set_page_config(
    page_title="COVID-19 Dashboard EE.UU.",
    layout="wide",
    page_icon="🦠"
)

st.title("📊 COVID-19 en Estados Unidos (2020-2021)")

st.markdown("""
Este dashboard interactivo muestra los datos de **COVID-19 en Estados Unidos** durante el periodo 2020-2021.

### 📚 Fuentes de Datos:
- [The COVID Tracking Project](https://covidtracking.com/data/download) - CC BY 4.0
- US Census Bureau (población por estado)
""")

# ============================================
# CARGA DE DATOS
# ============================================

@st.cache_data(show_spinner="Cargando datos COVID-19...")
def cargar_datos_crudos():
    """Carga los datos crudos desde data/raw/covid_states_daily.csv"""
    
    try:
        ruta_raw = Path("data/raw/covid_states_daily.csv")
        if not ruta_raw.exists():
            st.error(f"❌ ERROR CRÍTICO: No se encontró el archivo en: {ruta_raw}")
            return None
        
        df_cruo = pd.read_csv(ruta_raw)
        print(f"✅ Cargado {len(df_cruo):,} registros desde {ruta_raw}")
        return df_cruo
        
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return None

@st.cache_data(show_spinner="Preparando datos...")
def preparar_datos(df_cruo):
    """Prepara los datos para visualización"""
    
    if df_cruo is None:
        return None
    
    try:
        df = df_cruo.copy()
        
        # Asegurar tipos de datos
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], errors='coerce')
        
        # Filtrar registros con fecha inválida
        df = df[df["fecha"].notna()] if "fecha" in df.columns else df
        
        print(f"✅ Datos preparados: {len(df):,} registros válidos")
        return df
        
    except Exception as e:
        st.error(f"❌ Error en preprocesamiento: {e}")
        return None

@st.cache_data(show_spinner="Agregando datos de población...")
def cargar_poblacion_census():
    """Carga datos de población del Census (si están disponibles)"""
    
    try:
        ruta_censo = Path("data/raw/poblacion_estados_census.csv")
        if not ruta_censo.exists():
            print("⚠️ Sin datos de población del Census")
            return None
        
        censo_df = pd.read_csv(ruta_censo)
        print(f"✅ Cargado {len(censo_df):,} registros de población desde {ruta_censo}")
        return censo_df
        
    except Exception as e:
        print(f"⚠️ No se pudo cargar población del Census: {e}")
        return None

@st.cache_data(show_spinner="Cargando datos finales...")
def cargar_final(df_cruo, censo):
    """Combina datos COVID con población (si está disponible)"""
    
    if df_cruo is None or (censo is not None and len(censo) == 0):
        return df_cruo
    
    try:
        # Si hay datos de población, intentar unirlos
        if censo is not None:
            # Buscar columnas comunes (nombre del estado)
            columnas_estados = ["estado", "NAME"]
            columna_comun = [col for col in columnas_estados if col.lower() in str(df_cruo.columns).lower()][0]
            columna_censo = [col for col in censo.columns if col.lower() == 'name' or 'state' in col.lower()][0]
            
            # Unir si hay población
            df_unido = pd.merge(df_cruo, censo[[columna_censo]], left_on=columna_estados[0], right_on=columna_censo, how='left')
            print(f"✅ Datos unidos con población: {len(df_unido):,} registros")
        else:
            df_unido = df_cruo
        
        return df_unido
        
    except Exception as e:
        print(f"⚠️ No se pudo unir población (opcional): {e}")
        return df_cruo

@st.cache_data(show_spinner="Procesando datos finales...")
def procesar_datos(df_con_poblacion=None):
    """Función principal que devuelve los datos finales"""
    
    if "df_final" in st.session_state:
        print("🔄 Usando datos en caché")
        return st.session_state['df_final']
    
    print("⏳ Procesando datos por primera vez...")
    
    # Cargar datos si no están cargados
    df_cruo = cargar_datos_crudos()
    if df_cruo is None:
        st.error("❌ No se pudieron cargar los datos crudos. Verifica que `data/raw/covid_states_daily.csv` esté en el repositorio.")
        return None
    
    # Cargar población si está disponible
    censo = cargar_poblacion_census()
    
    # Combinar datos
    df_con_poblacion = cargar_final(df_cruo, censo)
    
    # Guardar en caché
    st.session_state['df_final'] = df_con_poblacion
    
    print(f"✅ Datos finales procesados: {len(df_con_poblacion):,} registros")
    return df_con_poblacion

# ============================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================

def grafico_evolution(df, metrica, fecha_inicio=None, fecha_fin=None):
    """Gráfico de evolución temporal con Plotly"""
    
    if metrica not in ["casos", "muertes", "hospitalizados"]:
        metrica = "casos"
    
    # Filtrar por rango de fechas si se especifica
    df_filtrado = df.copy()
    if fecha_inicio and fecha_fin and "fecha" in df.columns:
        mask = (df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)
        df_filtrado = df[mask]
    
    fig = go.Figure()
    
    if len(df_filtrado) > 0:
        fig.add_trace(go.Scatter(
            x=df_filtrado["fecha"],
            y=df_filtrada[metrica],
            mode='lines+markers',
            name=metrica.capitalize(),
            line=dict(color='#2a78d6', width=2),
            hovertemplate=f"<b>%{{x}}</b><br>%{{y:,.0f}}<extra></extra>"
        ))
    
    fig.update_layout(
        title=f"Evolución de {metrica.upper()} en EE.UU. (2020-2021)",
        xaxis_title="Fecha",
        yaxis_title=metrica.capitalize(),
        hovermode='x unified',
        template='plotly_white',
        height=500,
        margin=dict(l=80, r=40, t=60, b=40)
    )
    
    return fig

def grafico_ranking(df, metrica):
    """Ranking por estado con barras horizontales"""
    
    if metrica not in ["casos", "muertes"]:
        metrica = "casos"
    
    # Agrupar y ordenar (Top 15)
    ranking = df.groupby("estado")[metrica].sum().nlargest(15).reset_index()
    ranking.columns = ["estado", "valor"]
    
    fig = go.Figure()
    
    if len(ranking) > 0:
        fig.add_trace(go.Bar(
            x=ranking["estado"],
            y=ranking["valor"],
            name=f'Top {len(ranking)} Estados por {metrica.upper()}',
            marker_color='#2a78d6',
            orientation='h',
            hovertemplate="<b>%{{x}}</b><br>%{{y:,.0f}}<extra></extra>"
        ))
        
        fig.update_layout(
            title=f"Top {len(ranking)} Estados por {metrica.upper()}",
            yaxis={'categoryorder': 'total ascending'},
            template='plotly_white',
            height=500,
            margin=dict(l=120, r=40, t=60, b=40)
        )
    
    return fig

def grafico_hospitalizados(df):
    """Gráfico de hospitalizados por estado"""
    
    if "hospitalizados" not in df.columns:
        st.info("ℹ️ El gráfico de hospitalizados requiere datos específicos. Mostrando casos en su lugar.")
        return grafico_evolution(df, "casos")
    
    # Agrupar por estado y calcular promedio diario
    top_estados = df.groupby("estado")["hospitalizados"].mean().nlargest(10)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_estados.index,
        y=top_estados.values,
        marker_color='#4a9c26',
        orientation='h',
        hovertemplate="<b>%{{x}}</b><br>%{{y:,.1f}}<extra></extra>"
    ))
    
    fig.update_layout(
        title="Hospitalizados Promedio por Estado (últimos 7 días)",
        template='plotly_white',
        height=500,
        margin=dict(l=120, r=40, t=60, b=40)
    )
    
    return fig

# ============================================
# PANEL LATERAL (Filtros)
# ============================================

def panel_lateral(df_datos):
    """Configura el panel lateral con filtros"""
    
    with st.sidebar:
        st.header("🎛️ Filtros del Dashboard")
        st.divider()
        
        # Selector de métrica principal
        metrica = st.selectbox(
            "Seleccionar métrica:",
            ["casos", "muertes", "hospitalizados"],
            help="Elige qué variable COVID-19 visualizar"
        )
        
        st.divider()
        
        # Rango temporal
        if "fecha" in df_datos.columns and len(df_datos) > 0:
            
            # Obtener fecha máxima y mínima válidas
            fechas_validas = pd.to_datetime(df_datos["fecha"]).dropna()
            fecha_fin = st.date_input(
                "Fecha final:", 
                value=fechas_validas.max().date(),
                max_value=fechas_validas.max().date()
            )
            
            # Por defecto, mostrar últimos 180 días desde la fecha final
            fecha_inicio = st.date_input(
                "Fecha inicial:", 
                value=(fechas_validas.max().date() - pd.Timedelta(days=180)).date(),
                min_value=fechas_validas.min().date(),
                max_value=fecha_fin,
                key="date_picker"
            )
        else:
            st.info("📅 No hay datos de fecha disponibles para filtrar")
            fecha_inicio = None
            fecha_fin = None
        
        st.divider()
        
        # Información de datos
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            total_registros = len(df_datos) if isinstance(df_datos, pd.DataFrame) else 0
            st.metric("Total Registros", f"{total_registros:,}".replace(",", "."))
        with info_col2:
            if "estado" in df_datos.columns and isinstance(df_datos, pd.DataFrame):
                estados_unicos = df_datos["estado"].nunique()
            else:
                estados_unicos = 0
            st.metric("Estados con Datos", f"{estados_unicos:,}".replace(",", "."))
        
        st.divider()
        
        # Información adicional
        with st.expander("📚 Sobre los datos"):
            st.markdown("""
            **Fuente:** The COVID Tracking Project & US Census Bureau
            
            **Licencia:** CC BY 4.0
            
            **Periodo cubierto:** Marzo 2020 - Julio 2021
            
            **Actualización:** Datos procesados del repositorio original
            
            Para más información:
            - [The COVID Tracking Project](https://covidtracking.com/data/download)
            """)
        
        st.divider()
        
        # Enlaces y créditos
        col1, col2 = st.columns(2)
        with col1:
            if metrica == "casos":
                st.info("📊 **Casos:** Total de infecciones confirmadas")
            elif metrica == "muertes":
                st.error("☠️ **Muertes:** Fallecimientos por COVID-19")
            else:
                st.success("🏥 **Hospitalizados:** Personas ingresadas en UCI")
        
        with col2:
            st.caption("""
            🔗 [Ver código en GitHub](https://github.com/IA-P1-BCN/EDA-Anna_Costa)
            
            🌐 Datos CC BY 4.0
            
            ℹ️ Este dashboard usa la versión simplificada de Streamlit Cloud para despliegue rápido y estable.
            """)

# ============================================
# PÁGINA PRINCIPAL
# ============================================

def main():
    """Renderiza el dashboard completo de COVID-19"""
    
    try:
        # Cargar datos finales
        df_con_poblacion = procesar_datos()
        
        if df_con_poblacion is None or len(df_con_poblacion) == 0:
            st.error("❌ No se pudieron cargar los datos. Verifica que los archivos CSV estén en el repositorio.")
            st.stop()
        
        # Actualizar panel lateral con datos cargados
        panel_lateral(df_con_poblacion)
        
        # Cabecera con título y descripción
        st.title("📊 COVID-19 Dashboard - Estados Unidos")
        st.markdown("""
        Este dashboard interactivo muestra los datos de **COVID-19 en Estados Unidos** durante el periodo 2020-2021.
        
        Usa los filtros del panel lateral para explorar:
        - 📈 Evolución temporal de casos, muertes o hospitalizados
        - 🏆 Ranking de estados por magnitud seleccionada
        - 🗺️ Comparativa por estado
        """)
        
        # Sección de métricas clave
        st.header("📊 Métricas Clave del Período")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_casos = df_con_poblacion["casos"].sum() if "casos" in df_con_poblacion.columns else 0
            st.metric(
                label="📦 Casos Totales", 
                value=f"{total_casos:,}".replace(",", "."),
                delta="Total acumulado",
                help="Suma total de casos confirmados en el periodo"
            )
        
        with col2:
            total_muertes = df_con_poblacion["muertes"].sum() if "muertes" in df_con_poblacion.columns else 0
            st.metric(
                label="☠️ Muertes Totales", 
                value=f"{total_muertes:,}".replace(",", "."),
                delta="Total acumulado",
                help="Suma total de fallecimientos confirmados"
            )
        
        with col3:
            if "hospitalizados" in df_con_poblacion.columns:
                pico = df_con_poblacion["hospitalizados"].max()
                st.metric(
                    label="🏥 Pico Hospitalizados", 
                    value=f"{pico:,}".replace(",", "."),
                    delta="+ Máximo histórico",
                    help="Mayor número simultáneo de hospitalizados registrados"
                )
            else:
                avg_hosp = df_con_poblacion["hospitalizados"].mean() if "hospitalizados" in df_con_poblacion.columns else 0
                st.metric(
                    label="🏥 Promedio Hospitalizados", 
                    value=f"{avg_hosp:.1f}".replace(",", "."),
                    delta="Promedio diario",
                    help="Valor medio de hospitalizados por día"
                )
        
        # Gráficos principales en pestañas
        st.header("📈 Visualización Interactiva")
        
        tab1, tab2 = st.tabs(["Evolución Temporal 📊", "Ranking por Estado 🏆"])
        
        with tab1:
            metrica_tab = st.selectbox("Métrica temporal:", ["casos", "muertes", "hospitalizados"], index=0)
            
            fig_evolucion = grafico_evolution(
                df_con_poblacion, 
                metrica_tab,
                fecha_inicio=fecha_inicio if "fecha" in df_con_poblacion.columns else None,
                fecha_fin=fecha_fin if "fecha" in df_con_poblacion.columns else None
            )
            
            st.plotly_chart(fig_evolucion, use_container_width=True)
            
            st.caption(f"📅 Mostrando datos desde {pd.to_datetime(df_con_poblacion['fecha']).min().date()} hasta {pd.to_datetime(df_con_poblacion['fecha']).max().date()}")
        
        with tab2:
            metrica_ranking = st.selectbox("Métrica de ranking:", ["casos", "muertes"], index=0)
            
            fig_ranking = grafico_ranking(df_con_poblacion, metrica_ranking)
            
            if len(fig_ranking.data) > 0:
                st.plotly_chart(fig_ranking, use_container_width=True)
            else:
                st.info("📋 No hay suficientes datos para mostrar ranking. Intenta con la métrica temporal.")
        
        # Tabla de resumen (expander opcional)
        with st.expander("📋 Ver tabla completa de datos"):
            
            if metrica == "casos":
                col_nombres = ["fecha", "estado", "casos"]
            elif metrica == "muertes":
                col_nombres = ["fecha", "estado", "muertes"]
            else:
                col_nombres = ["fecha", "estado", "hospitalizados"]
            
            df_display = df_con_poblacion[col_nombres]
            st.dataframe(df_display.head(200), hide_index=True, use_container_width=True)
        
        # Footer con créditos
        st.markdown("---")
        st.caption("""
        **COVID-19 Dashboard** | Fuente: The COVID Tracking Project & US Census Bureau
        
        📚 Código fuente disponible en [GitHub](https://github.com/IA-P1-BCN/EDA-Anna_Costa)
        
        ℹ️ Este dashboard usa la versión simplificada de Streamlit Cloud para despliegue rápido y estable.
        
        🌐 Datos CC BY 4.0 - The COVID Tracking Project
        """)
        
    except Exception as e:
        st.error(f"❌ Error al ejecutar el dashboard: {e}")
        import traceback
        st.code(traceback.format_exc())

# Ejecutar app cuando se llama directamente
if __name__ == "__main__":
    main()
"""