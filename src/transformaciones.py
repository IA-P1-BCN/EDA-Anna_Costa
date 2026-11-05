"""Transformaciones de las variables: media móvil para las series y logaritmo para las distribuciones sesgadas."""

import numpy as np
import pandas as pd

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def media_movil(
    df: pd.DataFrame, columnas: list, ventana: int = 7, minimo: int = 4, sufijo: str = "_7d"
) -> pd.DataFrame:
    """Añade la media móvil de cada columna, calculada dentro de cada estado.

    Con `minimo` días con dato basta para calcularla, así un NaN suelto (una corrección) no deja la semana vacía.
    """
    df = df.sort_values(["estado", "fecha"]).copy()
    for columna in columnas:
        df[columna + sufijo] = df.groupby("estado")[columna].transform(
            lambda s: s.rolling(ventana, min_periods=minimo).mean())
    return df


def efecto_dia_semana(serie: pd.Series, ventana: int = 7) -> pd.Series:
    """Cuánto se aparta cada día de la semana de su media de 7 días centrada (1 = igual que la media)."""
    relacion = serie / serie.rolling(ventana, center=True).mean()
    efecto = relacion.groupby(relacion.index.day_of_week).mean()
    efecto.index = [DIAS_SEMANA[d] for d in efecto.index]
    return efecto


def log10_1p(valores):
    """log10(1 + x): comprime las colas largas y admite ceros (log10(1) = 0)."""
    return np.log10(1 + valores)


def asimetria(df: pd.DataFrame, columnas: list) -> pd.DataFrame:
    """Asimetría (skew) de cada columna antes y después de aplicar log10(1 + x)."""
    return pd.DataFrame({
        "asimetria_original": df[columnas].skew(),
        "asimetria_log": log10_1p(df[columnas]).skew(),
    })
