"""Datos del dashboard (app.py): carga, filtros y las tablas que dibuja cada gráfico.

Aquí no hay nada de Streamlit, así que todo se puede probar con pytest.
"""

from pathlib import Path

import pandas as pd

from src.graficos import AZUL, NARANJA, VERDE
from src.pipeline import CARPETA_PROCESSED, CARPETA_RAW, SALIDAS, ejecutar
from src.poblacion import por_100k
from src.variables import REGIONES

# Lo que se puede elegir en el gráfico de evolución: columna diaria y color de la magnitud.
METRICAS = {
    "Casos nuevos": ("casos_nuevos", AZUL),
    "Muertes nuevas": ("muertes_nuevas", NARANJA),
    "Hospitalizados": ("hospitalizados_actuales", VERDE),
}

# El ranking compara totales del periodo, así que solo tiene sentido con incrementos diarios.
METRICAS_RANKING = {"Casos": "casos_nuevos", "Muertes": "muertes_nuevas"}

REGIONES_DASHBOARD = [*REGIONES, "Territorios"]

# Columnas de la pestaña "Datos", con el nombre que ve el usuario.
COLUMNAS_TABLA = {
    "fecha": "Fecha",
    "estado": "Estado",
    "nombre_estado": "Nombre",
    "region": "Región",
    "casos_nuevos": "Casos nuevos",
    "muertes_nuevas": "Muertes nuevas",
    "hospitalizados_actuales": "Hospitalizados",
    "casos_100k_7d": "Casos por 100.000 (media 7 días)",
    "muertes_100k_7d": "Muertes por 100.000 (media 7 días)",
    "positividad_7d": "Positividad (7 días)",
}


def cargar_final(processed: Path = CARPETA_PROCESSED, raw: Path = CARPETA_RAW) -> pd.DataFrame:
    """Lee el fichero final del pipeline; si no existe (p. ej. en el servidor), lo genera."""
    ruta = Path(processed) / SALIDAS["final"]
    if not ruta.exists():
        ejecutar(raw, processed)
    return pd.read_csv(ruta, parse_dates=["fecha", "semana"])


def estados_de(df: pd.DataFrame, regiones: list[str]) -> dict[str, str]:
    """{código: "Nombre (código)"} de los estados de esas regiones, ordenados por nombre."""
    filas = df[df["region"].isin(regiones)].drop_duplicates("estado")
    nombres = filas["nombre_estado"].fillna(filas["estado"])
    etiquetas = dict(zip(filas["estado"], nombres + " (" + filas["estado"] + ")"))
    return dict(sorted(etiquetas.items(), key=lambda par: par[1]))


def filtrar(df: pd.DataFrame, regiones: list[str], estados: list[str], desde,
            hasta) -> pd.DataFrame:
    """Filas de las regiones y fechas elegidas; sin estados elegidos, todos los de la región."""
    mascara = df["region"].isin(regiones) & df["fecha"].between(pd.Timestamp(desde),
                                                                  pd.Timestamp(hasta))
    if estados:
        mascara &= df["estado"].isin(estados)
    return df[mascara]


def resumen(df: pd.DataFrame) -> dict:
    """Cifras de cabecera de la selección.

    Los totales son la suma de los datos diarios del periodo. Las tasas por 100.000 habitantes
    solo cuentan los estados con población (los territorios pequeños no están en el censo).
    """
    con_poblacion = df.dropna(subset=["poblacion"])
    poblacion = con_poblacion.drop_duplicates("estado")["poblacion"].sum()
    hospitalizados = df.groupby("fecha")["hospitalizados_actuales"].sum(min_count=1)
    pico = hospitalizados.idxmax() if hospitalizados.notna().any() else pd.NaT
    return {
        "casos": df["casos_nuevos"].sum(),
        "muertes": df["muertes_nuevas"].sum(),
        "casos_100k": (por_100k(con_poblacion["casos_nuevos"].sum(), poblacion)
                       if poblacion else None),
        "muertes_100k": (por_100k(con_poblacion["muertes_nuevas"].sum(), poblacion)
                         if poblacion else None),
        "pico_hospitalizados": hospitalizados.max(),
        "fecha_pico": pico,
    }


def serie_diaria(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Suma de la selección cada día y su media de 7 días (con al menos 4 días con dato)."""
    diaria = df.groupby("fecha")[columna].sum(min_count=1)
    return pd.DataFrame({"diaria": diaria, "media_7d": diaria.rolling(7, min_periods=4).mean()})


def ranking_100k(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Total del periodo por cada 100.000 habitantes en cada estado, de mayor a menor."""
    con_poblacion = df.dropna(subset=["poblacion"])
    tabla = con_poblacion.groupby(["estado", "nombre_estado", "region"], as_index=False).agg(
        total=(columna, "sum"), poblacion=("poblacion", "first"))
    tabla["por_100k"] = por_100k(tabla["total"], tabla["poblacion"])
    return tabla.sort_values("por_100k", ascending=False, ignore_index=True)


def hospitalizados_por_region(df: pd.DataFrame) -> pd.DataFrame:
    """Hospitalizados por cada 100.000 habitantes en cada región, día a día (media de 7 días).

    Cada día se divide entre la población de los estados que publicaron el dato ese día, para que
    los estados que aún no publicaban (primavera de 2020) no bajen la tasa de su región.
    """
    con_dato = df.dropna(subset=["poblacion", "hospitalizados_actuales"])
    por_dia = con_dato.groupby(["region", "fecha"])[["hospitalizados_actuales", "poblacion"]].sum()
    tasa = por_100k(por_dia["hospitalizados_actuales"], por_dia["poblacion"]).unstack("region")
    return tasa.rolling(7, min_periods=4).mean()


def tabla_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Las filas de la selección (lo más reciente primero) con columnas en castellano."""
    return (df.sort_values(["fecha", "estado"], ascending=[False, True])[list(COLUMNAS_TABLA)]
            .rename(columns=COLUMNAS_TABLA).reset_index(drop=True))


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def marcas_fecha(desde, hasta, maximo: int = 8) -> tuple[list[pd.Timestamp], list[str]]:
    """Marcas del eje de fechas con los meses en castellano (Streamlit no traduce los de plotly).

    Con tres meses o más, una marca el día 1 de cada mes ("mar 2020"), o de cada dos o tres meses
    si no caben `maximo`. En periodos más cortos, marcas cada pocos días ("5 nov").
    """
    desde, hasta = pd.Timestamp(desde), pd.Timestamp(hasta)
    meses = pd.date_range(desde, hasta, freq="MS")
    if len(meses) >= 3:
        marcas = meses[::-(-len(meses) // maximo)]
        return list(marcas), [f"{MESES[m.month - 1]} {m.year}" for m in marcas]
    paso = max(1, -(-(hasta - desde).days // maximo))
    marcas = pd.date_range(desde, hasta, freq=f"{paso}D")
    return list(marcas), [f"{m.day} {MESES[m.month - 1]}" for m in marcas]
