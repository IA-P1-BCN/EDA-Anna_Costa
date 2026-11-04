"""Revisión de datos de calidad dudosa: valores imposibles, incoherencias entre columnas y correcciones."""

import numpy as np
import pandas as pd

# Reglas de coherencia entre columnas. Cada una devuelve True en las filas que la incumplen.
# Las comparaciones con NaN dan False: una fila sin dato no incumple nada.
REGLAS_COHERENCIA = {
    "positivos_sobre_tests": (
        "Más positivos acumulados que tests acumulados",
        lambda df: df["casos_acum"] > df["tests_acum"],
    ),
    "muertes_sobre_casos": (
        "Más muertes acumuladas que casos acumulados",
        lambda df: df["muertes_acum"] > df["casos_acum"],
    ),
    "uci_sobre_hospitalizados": (
        "Más pacientes en UCI que hospitalizados",
        lambda df: df["uci_actuales"] > df["hospitalizados_actuales"],
    ),
    "ventilador_sobre_uci": (
        "Más pacientes con respirador que en UCI",
        lambda df: df["ventilador_actuales"] > df["uci_actuales"],
    ),
    "recuperados_sobre_casos": (
        "Recuperados más muertes por encima de los casos",
        lambda df: df["recuperados"] + df["muertes_acum"] > df["casos_acum"],
    ),
}

# Incremento diario y columna acumulada de la que sale.
PARES_INCREMENTO = {
    "casos_nuevos": "casos_acum",
    "muertes_nuevas": "muertes_acum",
    "tests_nuevos": "tests_acum",
}


def revisar_coherencia(df: pd.DataFrame, reglas: dict = REGLAS_COHERENCIA) -> pd.DataFrame:
    """Una columna booleana por regla: True si la fila la incumple."""
    return pd.DataFrame({nombre: regla(df) for nombre, (_, regla) in reglas.items()}, index=df.index)


def resumir_marcas(df: pd.DataFrame, marcas: pd.DataFrame, descripciones: dict | None = None) -> pd.DataFrame:
    """Para cada marca: cuántas filas, cuántos estados, los más afectados y entre qué fechas."""
    filas = []
    for nombre in marcas.columns:
        afectadas = df.loc[marcas[nombre]]
        filas.append({
            "marca": nombre,
            "descripcion": (descripciones or {}).get(nombre, ""),
            "filas": len(afectadas),
            "estados": afectadas["estado"].nunique(),
            "principales": ", ".join(f"{e} ({n})" for e, n in afectadas["estado"].value_counts().head(3).items()),
            "desde": afectadas["fecha"].min(),
            "hasta": afectadas["fecha"].max(),
        })
    return pd.DataFrame(filas).set_index("marca")


def comprobar_incrementos(df: pd.DataFrame, pares: dict = PARES_INCREMENTO) -> pd.DataFrame:
    """Comprueba que cada incremento diario es la diferencia entre dos acumulados seguidos del mismo estado."""
    df = df.sort_values(["estado", "fecha"])
    filas = []
    for incremento, acumulado in pares.items():
        diferencia = df.groupby("estado")[acumulado].diff()
        comparables = diferencia.notna() & df[incremento].notna()
        distintos = (df[incremento] != diferencia) & comparables
        filas.append({"incremento": incremento, "acumulado": acumulado, "filas_comparadas": int(comparables.sum()),
                      "no_coinciden": int(distintos.sum()), "acumulado_baja": int((diferencia < 0).sum())})
    return pd.DataFrame(filas).set_index("incremento")


def resumir_correcciones(df_crudo: pd.DataFrame, columnas: list) -> pd.DataFrame:
    """Incrementos negativos de los datos sin limpiar: cuántos, cuánto restan y qué estados los tienen."""
    filas = []
    for columna in columnas:
        negativos = df_crudo[df_crudo[columna] < 0]
        peor = negativos.nsmallest(1, columna)
        filas.append({
            "columna": columna,
            "correcciones": len(negativos),
            "estados": negativos["estado"].nunique(),
            "total_restado": negativos[columna].sum(),
            "mayor": peor[columna].iloc[0] if len(peor) else np.nan,
            "mayor_estado": peor["estado"].iloc[0] if len(peor) else "",
            "mayor_fecha": peor["fecha"].iloc[0] if len(peor) else pd.NaT,
        })
    return pd.DataFrame(filas).set_index("columna")


def diferencia_totales(df: pd.DataFrame, pares: dict = PARES_INCREMENTO) -> pd.DataFrame:
    """Suma de los incrementos frente al último acumulado de cada estado.

    Al pasar las correcciones a NaN, la suma de los incrementos queda algo por encima del acumulado oficial.
    """
    ultimo = df.sort_values("fecha").groupby("estado").tail(1)
    filas = []
    for incremento, acumulado in pares.items():
        suma, oficial = df[incremento].sum(), ultimo[acumulado].sum()
        filas.append({"incremento": incremento, "suma_incrementos": suma, "ultimo_acumulado": oficial,
                      "diferencia": suma - oficial, "diferencia_pct": (suma - oficial) / oficial * 100})
    return pd.DataFrame(filas).set_index("incremento")


def marcar_ceros_sin_publicar(
    df: pd.DataFrame, columna: str = "casos_nuevos", acumulado: str = "casos_acum", minimo: float = 1000
) -> pd.Series:
    """Días con incremento 0 en un estado que ya llevaba `minimo` casos: casi seguro, días sin publicar.

    Con la epidemia en marcha, un estado con miles de casos no pasa un día entero sin ninguno. Los casos de ese
    día se publican al siguiente, así que el valor no se cambia: solo se marca.
    """
    return (df[columna] == 0) & (df[acumulado] >= minimo)


def tratar_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica los tratamientos de este análisis de calidad y añade una marca por tipo de dato dudoso.

    - Positivos por encima de los tests: los tests de esa fila no son fiables, pasan a NaN.
    - Respirador por encima de UCI y recuperados por encima de los casos: se marcan y no se tocan
      (son columnas que no se usan en las conclusiones).
    - Días sin publicar casos: se marcan y no se tocan; la media de 7 días los reparte.
    """
    df = df.copy()
    marcas = revisar_coherencia(df)
    for nombre in ["positivos_sobre_tests", "ventilador_sobre_uci", "recuperados_sobre_casos"]:
        df[nombre] = marcas[nombre]
    df.loc[df["positivos_sobre_tests"], ["tests_acum", "tests_nuevos"]] = np.nan
    df["cero_sin_publicar"] = marcar_ceros_sin_publicar(df)
    return df
