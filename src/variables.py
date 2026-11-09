"""Variables derivadas: partes de la fecha, ola, región, positividad y letalidad aparente."""

import pandas as pd

# Regiones del Census Bureau de EE. UU. Los territorios no pertenecen a ninguna.
REGIONES = {
    "Noreste": ["CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"],
    "Medio Oeste": ["IL", "IN", "MI", "OH", "WI", "IA", "KS", "MN", "MO", "NE", "ND", "SD"],
    "Sur": ["DE", "DC", "FL", "GA", "MD", "NC", "SC", "VA", "WV", "AL", "KY", "MS", "TN", "AR", "LA", "OK", "TX"],
    "Oeste": ["AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY", "AK", "CA", "HI", "OR", "WA"],
}
REGION_POR_ESTADO = {estado: region for region, estados in REGIONES.items() for estado in estados}

# Último día de cada ola. Los dos primeros cortes son los valles de la media de 7 días de casos
# nacionales (se calculan y se comprueban en el notebook 03); el último es el final de los datos.
OLAS = {
    "1 · primavera 2020": "2020-06-09",
    "2 · verano 2020": "2020-09-12",
    "3 · otoño-invierno 2020-21": "2021-03-07",
}


def encontrar_valle(serie: pd.Series, desde: str, hasta: str) -> pd.Timestamp:
    """Fecha del valor mínimo de una serie temporal dentro de un intervalo."""
    return serie.loc[desde:hasta].idxmin()


def partes_fecha(df: pd.DataFrame) -> pd.DataFrame:
    """Añade `año`, `mes` y `semana` (el lunes con el que empieza la semana del dato)."""
    df = df.copy()
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["semana"] = df["fecha"].dt.to_period("W-SUN").dt.start_time
    return df


def asignar_ola(df: pd.DataFrame, olas: dict = OLAS) -> pd.DataFrame:
    """Añade `ola`, una categoría ordenada según la fecha."""
    df = df.copy()
    cortes = [pd.Timestamp.min, *pd.to_datetime(list(olas.values()))]
    df["ola"] = pd.cut(df["fecha"], bins=cortes, labels=list(olas), right=True)
    return df


def asignar_region(df: pd.DataFrame, regiones: dict = REGION_POR_ESTADO) -> pd.DataFrame:
    """Añade `region`; los territorios quedan como "Territorios"."""
    df = df.copy()
    df["region"] = df["estado"].map(regiones).fillna("Territorios")
    return df


def positividad_7d(df: pd.DataFrame, ventana: int = 7, maximo: float | None = 1.0) -> pd.Series:
    """Casos nuevos / tests nuevos de los últimos `ventana` días de cada estado.

    Se suman casos y tests de la semana antes de dividir: el cociente de un solo día es muy
    ruidoso (un día sin tests notificados da valores por encima del 100 %). Los valores por
    encima de `maximo` no son posibles (series de casos y tests desfasadas) y pasan a NaN;
    con `maximo=None` se devuelven tal cual.
    """
    ordenado = df.sort_values(["estado", "fecha"])
    por_estado = ordenado.groupby("estado")
    casos = por_estado["casos_nuevos"].transform(lambda s: s.rolling(ventana, min_periods=4).sum())
    tests = por_estado["tests_nuevos"].transform(lambda s: s.rolling(ventana, min_periods=4).sum())
    positividad = casos / tests.where(tests > 0)
    if maximo is not None:
        positividad = positividad.where(positividad <= maximo)
    return positividad.reindex(df.index)


def letalidad_aparente(df: pd.DataFrame, minimo_casos: int = 1000) -> pd.Series:
    """Muertes acumuladas / casos acumulados, solo cuando el estado ya tiene `minimo_casos` casos.

    Es "aparente" porque depende de cuántos casos se detectan: con pocos tests sale más alta.
    """
    casos = df["casos_acum"].where(df["casos_acum"] >= minimo_casos)
    return df["muertes_acum"] / casos


def crear_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Añade todas las variables derivadas a los datos limpios."""
    df = partes_fecha(df)
    df = asignar_ola(df)
    df = asignar_region(df)
    df["positividad_7d"] = positividad_7d(df)
    df["letalidad_aparente"] = letalidad_aparente(df)
    return df

