# 🦠 COVID-19 EDA Dashboard

**Dashboard interactivo de análisis exploratorio de datos sobre COVID-19 en Estados Unidos (2020-2021)**

[![Streamlit Cloud](https://img.shields.io/badge/Made%20with-Streamlit-orange)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📊 Características Principales

### 🎯 Análisis Interactivo
- **Métricas Clave**: Casos acumulados, muertes acumuladas, hospitalizaciones actuales
- **Visualización por Estado**: Ranking de los 30 estados con mayor impacto
- **Comparación Multi-Métrica**: Vista comparativa simultánea entre diferentes variables
- **Evolución Temporal**: Análisis de tendencias a lo largo del tiempo

### 🔍 Funcionalidades

| Feature | Descripción |
|---------|-------------|
| 📊 **Selector de Métricas** | Elige entre casos, muertes, hospitalizaciones o pruebas realizadas |
| 📅 **Filtros Temporales** | "Completo" o rangos de -30/-60/-90 días desde la última fecha del dataset |
| 🗺️ **Datos por Estado** | Tabla interactiva Top 30 con todas las métricas disponibles |
| 🔍 **Comparador** | Vista comparativa múltiple en una sola pantalla |
| 💾 **Exportación CSV** | Descarga de datos filtrados para análisis externo |

## 🚀 Despliegue en Streamlit Cloud

### Opción 1: Desplegado Automático (Recomendado)

Este repositorio está listo para desplegarse automáticamente. Simplemente:

1. Ve a [https://streamlit.io/cloud/new](https://streamlit.io/cloud/new)
2. Conecta tu cuenta de GitHub
3. Selecciona este repositorio: `EDA-Anna_Costa`
4. Elige la rama `main`
5. Streamlit Cloud lo desplegará automáticamente

### Opción 2: Despliegue Manual

Si prefieres control total sobre el despliegue:

```bash
# Clona el repositorio
git clone https://github.com/TU_USUARIO/EDA-COVID.git

# Entra en la carpeta
cd EDA-COVID

# Instala dependencias (si es necesario)
pip install -r requirements.txt

# Inicia la app
streamlit run app.py
```

## 📦 Estructura del Proyecto

```
EDA-Anna_Costa/
├── app.py                    # Dashboard Streamlit principal
├── data/
│   ├── processed/           # Datos procesados y listos para análisis
│   │   ├── covid_estados_final.csv    (6.2 MB - Dataset principal)
│   │   ├── covid_estados_limpio.csv   (2.5 MB - Versión alternativa)
│   │   └── covid_estados_poblacion.csv (5.7 MB - Datos demográficos)
│   └── raw/                 # Datos originales
├── notebooks/                # Cuadernos de análisis Jupyter
│   ├── 01_eda_covid.ipynb     # Carga y exploración inicial
│   ├── 02_outliers.ipynb      # Detección de valores atípicos
│   ├── 03_variables_y_agrupaciones.ipynb
│   ├── 04_correlaciones_y_tendencias.ipynb
│   └── ...
├── reports/                  # Informes y presentaciones
│   ├── informe_ejecutivo.pdf    # Resumen ejecutivo (350 KB)
│   └── presentacion.pdf         # Slides de presentación (508 KB)
├── .streamlit/              # Configuración del dashboard
│   └── config.toml            # Tema y personalización
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

## 📊 Métricas Disponibles

El dashboard permite analizar las siguientes métricas:

| Métrica | Descripción | Unidad |
|---------|-------------|--------|
| `casos_acum` | Casos acumulados desde inicio de pandemia | N° casos |
| `muertes_acum` | Muertes confirmadas | N° muertes |
| `hospitalizados_actuales` | Pacientes actualmente hospitalizados | N° pacientes |
| `tests_acum` | Pruebas realizadas totales | N° pruebas |

## 📅 Periodo de Datos

- **Inicio**: Marzo 2020
- **Fin**: Diciembre 2021
- **Estado**: Estados Unidos (50 estados + territorios)

> ⚠️ **Importante**: Los filtros temporales se aplican relativos a la última fecha disponible del dataset, no a "hoy". Esto asegura que siempre se muestren datos históricos reales.

## 🛠️ Tecnologías

| Tecnología | Versión |
|------------|---------|
| Python | 3.10+ |
| Pandas | Latest |
| Streamlit | Latest |
| NumPy | Latest |

## 📚 Licencia

MIT License - [Ver licencia completa](LICENSE)

## 👤 Autor

**IA P1-BCN Maestría 2º** - Proyecto de Análisis Exploratorio de Datos

---

[![GitHub](https://img.shields.io/badge/GitHub-EDA--Anna_Costa-blue.svg)](https://github.com/IA-P1-BCN)