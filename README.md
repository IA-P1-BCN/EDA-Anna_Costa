# 🦠 COVID-19 EDA Dashboard

<div align="center">

**[🌐 Acceder al Dashboard](https://eda-costanna.streamlit.app/)**  
*Dashboard interactivo de análisis exploratorio de datos sobre COVID-19 en Estados Unidos (2020-2021)*

[![Streamlit Cloud](https://img.shields.io/badge/Made%20with-Streamlit-orange)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 📊 Características Principales

### 🎯 Análisis Interactivo Completo
- **Métricas Clave**: Casos acumulados, muertes acumuladas, hospitalizaciones actuales, pruebas realizadas
- **Visualización por Estado**: Ranking de los estados con mayor impacto (top 15)
- **Comparación Multi-Métrica**: Vista comparativa simultánea entre diferentes variables
- **Evolución Temporal**: Análisis de tendencias semanales a lo largo del tiempo (2020-2021)

### 📈 Visualizaciones con Plotly Interactivo

| Gráfico | Descripción |
|---------|-------------|
| 📊 **Top Estados** | Barras horizontales interactivas con top 15 estados por impacto |
| 🔗 **Correlación** | Heatmap de matriz de correlación entre métricas clave |
| 📅 **Tendencias Temporales** | Gráfico de líneas mostrando evolución semanal del top 5 estados |
| 🗺️ **Distribución Regional** | Treemap interactivo de distribución por región (cuando disponible) |

### 🔍 Funcionalidades Avanzadas

| Feature | Descripción |
|---------|-------------|
| 📊 **Selector de Métricas** | Elige entre casos, muertes, hospitalizaciones o pruebas realizadas |
| 📅 **Filtros Temporales Inteligentes** | "Todo el periodo" o rangos de -30/-60/-90 días desde la última fecha del dataset |
| 📋 **Tabla Interactiva** | Vista detallada por estado con scroll y filtrado nativo |
| ⚖️ **Comparador Multi-Métrica** | Comparativa simultánea entre casos, muertes y hospitalizaciones |
| 💾 **Datos Exportables** | Tablas con datos formateados para análisis externo |

## 🚀 Despliegue en Streamlit Cloud

### ✅ App Ya Desplegada (Live)

🌐 **[Acceder ahora: https://eda-costanna.streamlit.app/](https://eda-costanna.streamlit.app/)**

El dashboard está completamente desplegado y funcionando. Simplemente accede con un clic!

### 📦 Instalación Local (Opcional)

Si deseas ejecutar el dashboard en tu propia máquina:

```bash
# Clona el repositorio
git clone https://github.com/costanna/EDA-COVID.git

# Entra en la carpeta
cd EDA-COVID

# Instala dependencias con uv (recomendado) o pip
uv sync                    # O: pip install -r requirements.txt

# Inicia la app
streamlit run app.py
```

## 📊 Métricas Disponibles

El dashboard permite analizar las siguientes métricas:

| Métrica | Descripción | Unidad | Tipo |
|---------|-------------|--------|------|
| `casos_acum` | Casos acumulados desde inicio de pandemia (2020) | N° casos | 🔴 Principal |
| `muertes_acum` | Muertes confirmadas por COVID-19 | N° muertes | 🔴 Crítico |
| `hospitalizados_actuales` | Pacientes actualmente hospitalizados por COVID | N° pacientes | 🟡 Secundario |
| `tests_acum` | Pruebas PCR/antígeno realizadas totales | N° pruebas | 🟢 Informativo |

### 📅 Periodo de Datos

- **Inicio**: 13 de enero de 2020
- **Fin**: 7 de marzo de 2021
- **Duración total**: 420 días
- **Cobertura geográfica**: 50 estados de EE.UU. + territorios

> ⚠️ **Nota importante**: Los filtros temporales se aplican relativos a la última fecha disponible del dataset (marzo 2021), no a "hoy". Esto asegura que siempre se muestren datos históricos reales y consistentes.

## 📁 Estructura del Proyecto

```
EDA-COVID/
├── app.py                          # Dashboard Streamlit principal (310 líneas)
├── data/
│   ├── processed/                  # Datos procesados y listos para análisis
│   │   └── covid_estados_final.csv    (6.2 MB - Dataset principal 628K registros)
│   └── raw/                        # Datos originales (si existen)
├── notebooks/                      # Cuadernos de análisis Jupyter
│   ├── 01_eda_covid.ipynb          # Carga y exploración inicial
│   ├── 02_outliers.ipynb           # Detección de valores atípicos
│   ├── 03_variables_y_agrupaciones.ipynb
│   └── 04_correlaciones_y_tendencias.ipynb
├── reports/                        # Informes y presentaciones
│   ├── informe_ejecutivo.pdf       # Resumen ejecutivo (350 KB)
│   └── presentacion.pdf            # Slides de presentación (508 KB)
├── .streamlit/                     # Configuración del dashboard
│   └── config.toml                 # Tema y personalización (modo oscuro, colores)
├── requirements.txt                # Dependencias Python
└── README.md                      # Esta documentación
```

## 🎨 Personalización del Dashboard

### 🖥️ Modos de Visualización

El dashboard está configurado con:
- **Modo Oscuro** por defecto (profesional y cómodo para visualizaciones largas)
- **Colores azules** para métricas principales (casos, muertes, hospitalizaciones)
- **Escalable** a diferentes tamaños de pantalla

### 📊 Gráficos Interactivos

Todos los gráficos Plotly son:
- ✅ **Hover tooltips**: Al pasar el mouse se muestra información detallada
- ✅ **Zoom y pan**: Navega entre los datos haciendo zoom
- ✅ **Animados**: Transiciones suaves entre estados
- ✅ **Responsive**: Se adaptan a diferentes tamaños de pantalla

## 📚 Librerías Utilizadas

```python
pandas           # Manipulación y análisis de datos
plotly.express   # Visualizaciones interactivas (bar, line, imshow, treemap)
streamlit        # Framework para el dashboard web
```

## 🔧 Configuración del Filtro Temporal

### Opciones disponibles en el sidebar:

1. **"Todo el periodo disponible"** 🟢
   - Muestra TODOS los datos desde enero 2020 hasta marzo 2021
   - Ideal para análisis completo y comparativas históricas

2. **"-30 días desde la última fecha"** 🟡  
   - Muestra solo los últimos 30 días del dataset (febrero-marzo 2021)
   - Útil para analizar tendencias recientes o picos de infección

3. **"-60/-90 días"**
   - Rangos intermedios para análisis más detallados
   - Permite comparar diferentes periodos históricos

## 📝 Información del Proyecto

- **Autor**: costanna
- **Maestría**: IA P1-BCN Maestría 2º
- **Fecha de creación**: 2026
- **Licencia**: MIT (código abierto)

## 🐛 Solución de Problemas

### Si los gráficos aparecen vacíos:
1. Verifica que la métrica seleccionada exista en el dataset
2. Asegúrate de no haber aplicado un filtro temporal muy restrictivo
3. Revisa el console del navegador para errores JavaScript

### Si la app no carga:
```bash
# Limpiar caché en Streamlit Cloud
Manage app → Clear cache → Rerun

# O reinstalar dependencias localmente
pip install -r requirements.txt --upgrade
```

## 📞 Contacto y Colaboración

- **Repo**: [GitHub - costanna/EDA-COVID](https://github.com/costanna/EDA-COVID)
- **Dashboard Live**: [Streamlit Cloud](https://eda-costanna.streamlit.app/)

---

<div align="center">
**Hecho con ❤️ y Streamlit para el análisis de datos del COVID-19**
</div>