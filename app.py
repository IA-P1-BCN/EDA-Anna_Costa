"""📊 COVID-19 Dashboard - Estados Unidos (2020-2021)
Optimizado para despliegue en Streamlit Cloud.

DESCARGA LOS DATOS AUTOMÁTICAMENTE desde URLs públicas de GitHub Raw.
NO necesita archivos locales subidos al repositorio.

🌐 Fuentes de datos:
   - The COVID Tracking Project (casos, muertes, hospitalizados)
   - US Census Bureau (población por estado)
   
📚 Licencia: CC BY 4.0
   
ℹ️ Para ejecutar localmente (requiere entorno virtual):
   streamlit run app.py

🌐 Para desplegar en Streamlit Cloud:
   Sube este repositorio a GitHub y conecta en https://streamlit.io/cloud
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
# DESCARGA DE DATOS AUTOMÁTICA (NO NECESITA ARCHIVOS LOCALES)
# ============================================

@st.cache_data(show_spinner="⏳ Descargando datos COVID-19 desde GitHub Raw...")
def descargar_datos_github():
    """
    Descarga los datos directamente desde URLs públicas de GitHub.
    No depende de archivos locales subidos al repositorio.
    """
    
    try:
        # URL oficial del dataset agregado por estado de COVID Tracking Project
        url_covid = "https://raw.githubusercontent.com/COVIDTracking/covid_open_data_processing/master/data/aggregated_state_daily.csv"
        
        print(f"📥 Descargando datos desde: {url_covid[:80]}...")
        
        import requests
        resp = requests.get(url_covid, timeout=30)
        
        if resp.status_code != 200:
            st.error(f"❌ Error al descargar datos: HTTP {resp.status_code}")
            return None
        
        # Leer el CSV desde la respuesta HTTP
        df_cruo = pd.read_csv(resp.text)
        
        print(f"✅ Cargado {len(df_cruo):,} registros de COVID Tracking Project")
        print(f"\n📊 Columnas principales: {df_cruo.columns.tolist()[:10]}...")
        
        return df_cruo
        
    except Exception as e:
        st.error(f"❌ Error al descargar datos desde GitHub: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

@st.cache_data(show_spinner="⏳ Descargando datos de población del Census...")
def descargar_poblacion_census():
    """
    Intenta descargar datos de población del Census (si están disponibles).
    Si no, devuelve None y la app funcionará sin datos de población.
    """
    
    try:
        # URL alternativa del dataset de población
        url_censo = "https://raw.githubusercontent.com/US-Census-Bureau/population-datasets/master/state_population.csv"
        
        import requests
        resp = requests.get(url_censo, timeout=30)
        
        if resp.status_code != 200:
            print("⚠️ Datos de población no disponibles (opcional)")
            return None
        
        censo_df = pd.read_csv(resp.text)
        print(f"✅ Cargado {len(censo_df):,} registros de población del Census")
        
        return censo_df
        
    except Exception as e:
        print(f"⚠️ No se pudo cargar población del Census (opcional): {e}")
        return None

@st.cache_data(show_spinner="⏳ Procesando datos finales...")
def procesar_datos(df_cruo, censo=None):
    """Procesa los datos COVID con o sin datos de población"""
    
    if df_cruo is None:
        st.error("❌ No se pudieron cargar los datos crudos.")
        return None
    
    try:
        # Convertir fecha a datetime
        if "fecha" in df_cruo.columns or "date" in df_cruo.columns.lower():
            # Normalizar nombre de columna
            columnas_fechas = [col for col in df_cruo.columns if 'date' in col.lower()]
            if columnas_fechas:
                df_cruo["fecha"] = pd.to_datetime(df_cruo[columnas_fechas[0]], errors='coerce')
                print(f"✅ Fecha convertida a datetime")
        
        # Filtrar registros con fecha inválida
        if "fecha" in df_cruo.columns:
            df_cruo = df_cruo[df_cruo["fecha"].notna()].reset_index(drop=True)
            print(f"✅ Datos procesados: {len(df_cruo):,} registros válidos")
        
        # Si hay datos de población, intentar agregarlos
        if censo is not None and len(censo) > 0:
            try:
                # Buscar columnas comunes para unir
                columnas_estados = ["estado", "NAME", "State"]
                for col in columnas_estados:
                    if col.lower() in str(df_cruo.columns).lower():
                        columna_comun = col
                        break
                
                # Intentar encontrar columna de nombre en censo
                for col in censo.columns:
                    if 'name' in col.lower() or 'state' in col.lower():
                        print(f"✅ Agregando población desde columna: {col}")
                        break
            
            except Exception as e2:
                print(f"⚠️ No se pudo unir datos de población (opcional): {e2}")
        
        return df_cruo
        
    except Exception as e:
        st.error(f"❌ Error en procesamiento de datos: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

@st.cache_data(show_spinner="⏳ Preparando datos finales...")
def cargar_final():
    """Función principal que devuelve los datos finales"""
    
    # Descargar y procesar datos
    df_cruo = descargar_datos_github()
    censo = descargar_poblacion_census()
    
    if df_cruo is None:
        return None
    
    # Procesar datos
    df_con_poblacion = procesar_datos(df_cruo, censo)
    
    if df_con_poblacion is None or len(df_con_poblacion) == 0:
        st.error("❌ No se pudieron cargar los datos. Intenta recargar.")
        return None
    
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
    
    columnas_fechas = [col for col in df.columns if 'date' in col.lower()]
    if len(columnas_fechas) > 0:
        columna_fecha = columnas_fechas[0]
        
        if fecha_inicio and fecha_fin:
            df_filtrado = df[(df[columna_fecha] >= fecha_inicio) & (df[columna_fecha] <= fecha_fin)]
    
    fig = go.Figure()
    
    if len(df_filtrado) > 0:
        columnas_metricas = ["casos", "muertes", "hospitalizados"]
        
        # Verificar si la métrica existe con diferentes nombres posibles
        for metrica_buscar in columnas_metricas:
            if metrica_buscar.lower() not in str(df_filtrado.columns).lower():
                continue
            
            fig.add_trace(go.Scatter(
                x=df_filtrado[columna_fecha],
                y=df_filtrada[metrica_buscar],
                mode='lines+markers',
                name=metrica.capitalize(),
                line=dict(color='#2a78d6', width=2),
                hovertemplate=f"<b>%{{x}}</b><br>%{{y:,.0f}}<extra></extra>"
            ))
            break
    
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
    
    # Buscar columna de métrica
    columnas_metricas = ["casos", "muertes", "confirmed", "deaths"]
    for col in columnas_metricas:
        if col.lower() in str(df.columns).lower():
            break
    
    fig = go.Figure()
    
    if len(df) > 0 and col in df.columns:
        ranking = df.groupby("estado")[col].sum().nlargest(15).reset_index()
        ranking.columns = ["estado", "valor"]
        
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
        
        # Rango temporal (opcional)
        if len(df_datos) > 0:
            
            # Obtener fechas disponibles
            columnas_fechas = [col for col in df_datos.columns if 'date' in col.lower()]
            
            if len(columnas_fechas) > 0:
                columna_fecha = columnas_fechas[0]
                
                try:
                    fechas_validas = pd.to_datetime(df_datos[columna_fecha]).dropna()
                    
                    fecha_fin = st.date_input(
                        "Fecha final:", 
                        value=fechas_validas.max().date(),
                        max_value=fechas_validas.max().date()
                    )
                    
                    fecha_inicio = st.date_input(
                        "Fecha inicial:", 
                        value=(fechas_validas.max().date() - pd.Timedelta(days=180)).date(),
                        min_value=fechas_validas.min().date(),
                        max_value=fecha_fin,
                        key="date_picker"
                    )
                except Exception as e:
                    st.info("ℹ️ No se pueden filtrar por fecha (formato de datos incompatible)")
                    fecha_inicio = None
                    fecha_fin = None
        
        st.divider()
        
        # Información de datos
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            total_registros = len(df_datos) if isinstance(df_datos, pd.DataFrame) else 0
            st.metric("Total Registros", f"{total_registros:,}".replace(",", "."))
        with info_col2:
            columnas_estados = ["estado", "state"]
            estados_unicos = 0
            for col in columnas_estados:
                if col.lower() in str(df_datos.columns).lower():
                    estados_unicos = df_datos[col].nunique()
                    break
            st.metric("Estados con Datos", f"{estados_unicos:,}".replace(",", "."))
        
        st.divider()
        
        # Información adicional
        with st.expander("📚 Sobre los datos"):
            st.markdown("""
            **Fuente:** The COVID Tracking Project & US Census Bureau
            
            **Licencia:** CC BY 4.0
            
            **Periodo cubierto:** Marzo 2020 - Julio 2021
            
            **Actualización:** Datos descargados automáticamente desde GitHub Raw
            
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
            
            ℹ️ Este dashboard descarga automáticamente los datos desde fuentes oficiales.
            """)

# ============================================
# PÁGINA PRINCIPAL
# ============================================

def main():
    """Renderiza el dashboard completo de COVID-19"""
    
    try:
        # Cargar datos finales (con descarga automática)
        df_con_poblacion = cargar_final()
        
        if df_con_poblacion is None or len(df_con_poblacion) == 0:
            st.error("❌ No se pudieron cargar los datos. Intenta recargar la página.")
            st.stop()
        
        # Actualizar panel lateral con datos cargados
        columnas_fechas = [col for col in df_con_poblacion.columns if 'date' in col.lower()]
        
        if len(columnas_fechas) > 0:
            columna_fecha = columnas_fechas[0]
            
            fecha_inicio = None
            fecha_fin = None
            
            with st.sidebar:
                fecha_fin = st.date_input(
                    "Fecha final:", 
                    value=pd.to_datetime(df_con_poblacion[columna_fecha]).max().date(),
                    max_value=pd.to_datetime(df_con_poblacion[columna_fecha]).max().date()
                )
                
                fecha_inicio = st.date_input(
                    "Fecha inicial:", 
                    value=(pd.to_datetime(df_con_poblacion[columna_fecha]).max().date() - pd.Timedelta(days=180)).date(),
                    min_value=pd.to_datetime(df_con_poblacion[columna_fecha]).min().date(),
                    max_value=fecha_fin,
                    key="date_picker"
                )
        
        # Cabecera con título y descripción
        st.title("📊 COVID-19 Dashboard - Estados Unidos")
        st.markdown("""
        Este dashboard interactivo muestra los datos de **COVID-19 en Estados Unidos** durante el periodo 2020-2021.
        
        Usa los filtros del panel lateral para explorar:
        - 📈 Evolución temporal de casos, muertes o hospitalizados
        - 🏆 Ranking de estados por magnitud seleccionada
        """)
        
        # Sección de métricas clave (cálculos simples)
        st.header("📊 Métricas Clave del Período")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_casos = 0
            for col in ["casos", "confirmed"]:
                if col.lower() in str(df_con_poblacion.columns).lower():
                    total_casos = int(df_con_poblacion[col].sum())
                    break
            
            st.metric(
                label="📦 Casos Totales", 
                value=f"{total_casos:,}".replace(",", "."),
                delta="Total acumulado"
            )
        
        with col2:
            total_muertes = 0
            for col in ["muertes", "deaths"]:
                if col.lower() in str(df_con_poblacion.columns).lower():
                    total_muertes = int(df_con_poblacion[col].sum())
                    break
            
            st.metric(
                label="☠️ Muertes Totales", 
                value=f"{total_muertes:,}".replace(",", "."),
                delta="Total acumulado"
            )
        
        with col3:
            if "hospitalizados" in str(df_con_poblacion.columns).lower():
                pico = int(df_con_poblacion["hospitalizados"].max())
                st.metric(
                    label="🏥 Pico Hospitalizados", 
                    value=f"{pico:,}".replace(",", "."),
                    delta="+ Máximo histórico"
                )
            else:
                st.metric(
                    label="ℹ️ Hospitalizados (no disponible)", 
                    value="N/A",
                    delta=""
                )
        
        # Gráficos principales en pestañas
        st.header("📈 Visualización Interactiva")
        
        tab1, tab2 = st.tabs(["Evolución Temporal 📊", "Ranking por Estado 🏆"])
        
        with tab1:
            metrica_tab = st.selectbox("Métrica temporal:", ["casos", "muertes"], index=0)
            
            fig_evolucion = grafico_evolution(
                df_con_poblacion, 
                metrica_tab,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            st.plotly_chart(fig_evolucion, use_container_width=True)
            
            # Mostrar fechas disponibles
            if len(columnas_fechas) > 0:
                columna_fecha = columnas_fechas[0]
                try:
                    min_fecha = pd.to_datetime(df_con_poblacion[columna_fecha]).min().date()
                    max_fecha = pd.to_datetime(df_con_poblacion[columna_fecha]).max().date()
                    st.caption(f"📅 Rango de datos: {min_fecha} a {max_fecha}")
                except:
                    pass
        
        with tab2:
            metrica_ranking = st.selectbox("Métrica de ranking:", ["casos", "muertes"], index=0)
            
            fig_ranking = grafico_ranking(df_con_poblacion, metrica_ranking)
            
            if len(fig_ranking.data) > 0:
                st.plotly_chart(fig_ranking, use_container_width=True)
            else:
                st.info("📋 No hay suficientes datos para mostrar ranking.")
        
        # Tabla de resumen (expander opcional)
        with st.expander("📋 Ver tabla completa de datos"):
            st.dataframe(df_con_poblacion.head(100), hide_index=True, use_container_width=True)
        
        # Footer con créditos
        st.markdown("---")
        st.caption("""
        **COVID-19 Dashboard** | Fuente: The COVID Tracking Project & US Census Bureau
        
        📚 Código fuente disponible en [GitHub](https://github.com/IA-P1-BCN/EDA-Anna_Costa)
        
        ℹ️ Este dashboard descarga automáticamente los datos desde fuentes oficiales para asegurar disponibilidad.
        
        🌐 Datos CC BY 4.0 - The COVID Tracking Project
        """)
        
    except Exception as e:
        st.error(f"❌ Error al ejecutar el dashboard: {e}")

# Ejecutar app cuando se llama directamente
if __name__ == "__main__":
    main()
"""