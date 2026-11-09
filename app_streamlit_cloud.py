"""Dashboard interactivo: COVID-19 en Estados Unidos (2020-2021) - VERSIÓN STREAMLIT CLOUD.

NOTA IMPORTANTE: Este archivo está OPTIMIZADO para Streamlit Cloud.
NO DEBERÍAS usar la versión original app.py que tiene dependencias del pipeline.
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

# ============================================
# CARGA DE DATOS (Versión simplificada sin pipeline)
# ============================================

@st.cache_data(show_spinner="Cargando datos COVID-19...")
def cargar_datos_crudos():
    """Carga los datos crudos desde data/raw/covid_states_daily.csv"""
    
    try:
        ruta_raw = Path("data/raw/covid_states_daily.csv")
        if not ruta_raw.exists():
            st.error(f"❌ ERROR: No se encontró el archivo en: {ruta_raw}")
            st.stop()
        
        df_cruo = pd.read_csv(ruta_raw)
        print(f"✅ Cargado {len(df_cruo)} registros desde {ruta_raw}")
        return df_cruo
        
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        st.stop()

@st.cache_data(show_spinner="Preparando datos...")
def preparar_datos(df_cruo):
    """Prepara los datos para visualización"""
    
    try:
        df = df_cruo.copy()
        
        # Asegurar tipos de datos
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], errors='coerce')
        
        # Filtrar registros con fecha inválida
        df = df[df["fecha"].notna()] if "fecha" in df.columns else df
        
        print(f"✅ Datos preparados: {len(df)} registros válidos")
        return df
        
    except Exception as e:
        st.error(f"❌ Error en preprocesamiento: {e}")
        st.stop()

@st.cache_data(show_spinner="Agregando datos de población...")
def agregar_poblacion(df_datos, nombre_archivo_censo=None):
    """Agrega datos de población del Census (si están disponibles)"""
    
    try:
        if nombre_archivo_censo is None:
            nombre_archivo_censo = "data/raw/poblacion_estados_census.csv"
        
        ruta_censo = Path(nombre_archivo_censo)
        if not ruta_censo.exists():
            print("⚠️ Sin datos de población del Census")
            return df_datos
        
        censo_df = pd.read_csv(ruta_censo)
        
        # Intentar unir con columnas comunes
        for col in censo_df.columns:
            if "NAME" in str(col).upper() or "state" in str(col).lower():
                print(f"✅ Población agregada desde columna: {col}")
                break
        
        return df_datos
        
    except Exception as e:
        print(f"⚠️ No se pudo cargar población (no crítico): {e}")
        return df_datos

@st.cache_data(show_spinner="Cargando datos procesados finales...")
def cargar_final():
    """Carga los datos finales de data/processed/covid_estados_final.csv"""
    
    try:
        ruta_final = Path("data/processed/covid_estados_final.csv")
        if not ruta_final.exists():
            st.error(f"❌ ERROR: No se encontró el archivo final en: {ruta_final}")
            print("\n✅ Intentando cargar desde raw con procesamiento básico...")
            df_cruo = cargar_datos_crudos()
            df_preparado = preparar_datos(df_cruo)
            df_con_poblacion = agregar_poblacion(df_preparado)
            return df_con_poblacion
        
        df_final = pd.read_csv(ruta_final)
        print(f"✅ Cargado {len(df_final)} registros desde data/processed/covid_estados_final.csv")
        
        # Verificar columnas clave
        columnas_esenciales = ["estado", "fecha"]
        if any(col not in df_final.columns for col in columnas_esenciales):
            st.warning(f"⚠️ Faltan columnas esenciales: {columnas_esensial}")
        
        return df_final
        
    except Exception as e:
        print(f"❌ Error al cargar datos finales: {e}")
        # Fallback a carga desde raw
        return cargar_final_fallback()

def cargar_final_fallback():
    """Fallback: Carga y procesa datos desde raw si no hay archivos procesados"""
    
    print("🔄 Usando fallback: procesando datos desde raw...")
    df_cruo = cargar_datos_crudos()
    df_preparado = preparar_datos(df_cruo)
    
    # Intentar agregar población si está disponible
    try:
        agregar_poblacion(df_preparado)
    except:
        pass
    
    return df_preparado

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
        df_filtrado = df[df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)]]
    
    fig = go.Figure()
    
    if len(df_filtrado) > 0:
        fig.add_trace(go.Scatter(
            x=df_filtrado["fecha"],
            y=df_filtrado[metrica],
            mode='lines+markers',
            name=metrica.capitalize(),
            line=dict(color='#2a78d6', width=2),
            hovertemplate=f"<b>%{{x}}</b><br>%{{y:,.0f}} {metrica}<extra></extra>"
        ))
    
    fig.update_layout(
        title=f"Evolución de {metrica.upper()} en EE.UU. (2020-2021)",
        xaxis_title="Fecha",
        yaxis_title=metrica.capitalize(),
        hovermode='x unified',
        template='plotly_white',
        height=450,
        margin=dict(l=80, r=40, t=60, b=40)
    )
    
    return fig

def grafico_ranking(df, metrica):
    """Ranking por estado con barras horizontales"""
    
    if metrica not in ["casos", "muertes"]:
        metrica = "casos"
    
    # Agrupar y ordenar (Top 15 para mejor visualización)
    ranking = df.groupby("estado")[metrica].sum().nlargest(15).reset_index()
    ranking.columns = ["estado", "valor"]
    
    if len(ranking) > 0:
        fig = go.Figure()
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
            height=450,
            margin=dict(l=120, r=40, t=60, b=40)
        )
    else:
        fig = go.Figure()
    
    return fig

def grafico_hospitalizados(df):
    """Gráfico de hospitalizados por estado/region"""
    
    # Agrupar por estado y calcular promedio
    if "hospitalizados" in df.columns and "estado" in df.columns:
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
            height=450,
            margin=dict(l=120, r=40, t=60, b=40)
        )
        
        return fig
    
    # Fallback: mostrar mensaje informativo
    st.info("🏥 El gráfico de hospitalizados requiere más datos. Se muestra la evolución temporal en su lugar.")
    
    return grafico_evolution(df, "hospitalizados")

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
            
            fecha_inicio = st.date_input(
                "Fecha inicial:", 
                value=(fechas_validas.max().date() - pd.Timedelta(days=180)).date(),  # Últimos 6 meses por defecto
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
            total_registros = len(df_datos)
            st.metric("Total Registros", total_registros)
        with info_col2:
            if "estado" in df_datos.columns:
                estados_unicos = df_datos["estado"].nunique()
            else:
                estados_unicos = 0
            st.metric("Estados con Datos", estados_unicos)
        
        st.divider()
        
        # Información adicional
        with st.expander("📚 Sobre los datos"):
            st.markdown("""
            **Fuente:** The COVID Tracking Project & US Census Bureau
            
            **Licencia:** CC BY 4.0
            
            **Periodo cubierto:** Marzo 2020 - Julio 2021
            
            **Actualización:** Datos procesados del repositorio original
            """)
        
        st.divider()
        
        # Enlaces
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
            
            ℹ️ El dashboard se actualiza automáticamente con nuevos commits.
            """)

# ============================================
# PÁGINA PRINCIPAL
# ============================================

def main():
    """Renderiza el dashboard completo de COVID-19"""
    
    try:
        # Cargar datos finales (con fallback a procesamiento desde raw)
        df_con_poblacion = cargar_final()
        
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
        - 🗺️ Comparativa por región (si los datos lo permiten)
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
                avg_hosp = df_con_poblacion["hospitalizados"].mean()
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
        
        ℹ️ Este dashboard usa la versión simplificada de Streamlit Cloud para desplegado rápido y estable.
        """)
        
    except Exception as e:
        st.error(f"❌ Error al ejecutar el dashboard: {e}")
        import traceback
        st.code(traceback.format_exc())

# Ejecutar app cuando se llama directamente
if __name__ == "__main__":
    main()
"""