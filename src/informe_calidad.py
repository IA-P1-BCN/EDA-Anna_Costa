"""Genera el informe de calidad de datos (reports/informe_calidad.md).

Uso, desde la raíz del repositorio y con el entorno activado:

    python -m src.informe_calidad

Lee los originales de data/raw/ (si faltan, los descarga), repite en memoria los pasos de
src/pipeline.py y calcula aquí todas las cifras del informe: qué faltaba, qué se corrigió y
qué quedó pendiente. Así el informe no se queda desfasado si cambian los datos o la limpieza.
"""

import logging
from pathlib import Path

import pandas as pd

from src.calidad import (REGLAS_COHERENCIA, diferencia_totales, resumir_correcciones,
                         resumir_marcas, revisar_coherencia)
from src.limpieza import (COLUMNAS, COLUMNAS_ATRASO, COLUMNAS_INCREMENTO, cargar_datos,
                          convertir_fecha, marcar_territorios, seleccionar_y_renombrar)
from src.pipeline import CARPETA_RAW, ORIGINALES, RAIZ, preparar_datos
from src.poblacion import cargar_poblacion
from src.variables import positividad_7d

RUTA_INFORME = RAIZ / "reports" / "informe_calidad.md"

# Columnas del original que se descartan por lo que son, no por sus nulos.
REPETIDAS = ["total", "posNeg", "hospitalized"]
METADATOS = ["hash", "lastUpdateEt", "dateModified", "checkTimeEt", "dateChecked"]

# Qué se hace con los nulos de cada columna conservada.
DECISION_NULOS = {
    "casos_acum": "No se imputan: antes del primer dato el estado aún no publicaba",
    "muertes_acum": "No se imputan: antes del primer dato el estado aún no publicaba",
    "tests_acum": "No se imputan: antes del primer dato el estado aún no publicaba",
    "fuente_tests": "Solo informativa (qué unidad usaba el estado)",
    "hospitalizados_actuales": (
        "No se imputan; la cifra nacional de la primavera de 2020 se queda corta"),
    "hospitalizados_nuevos": (
        "Columna no usada en las conclusiones (atrasos y cambios de definición)"),
    "uci_actuales": "Solo como referencia; no se usa en las conclusiones",
    "ventilador_actuales": "Solo como referencia; no se usa en las conclusiones",
    "recuperados": "Solo como referencia; cada estado la definía a su manera",
}

# Por qué cada marca deja el valor como está.
MOTIVO_MARCA = {
    "atraso_casos": (
        "Los casos existieron, solo se publicaron tarde; la media de 7 días los reparte"),
    "atraso_muertes": (
        "Las muertes existieron, solo se publicaron tarde; la media de 7 días las reparte"),
    "atraso_hospitalizados": "La columna `hospitalizados_nuevos` no se usa en las conclusiones",
    "ventilador_sobre_uci": "Puede haber respiradores fuera de la UCI; columna no usada",
    "recuperados_sobre_casos": "Cada estado definía «recuperado» a su manera; columna no usada",
    "cero_sin_publicar": "Los casos se publican al día siguiente; la media de 7 días los reparte",
}

# Volcado de muertes de Ohio que dura varios días: el criterio de atrasos solo marca el mayor.
VOLCADO_VARIOS_DIAS = ("OH", "2021-02-11", "2021-02-13")

# Meses en los que se mira cuántos estados publicaban los hospitalizados.
MESES_COBERTURA = ["2020-03", "2020-04", "2020-07", "2021-01"]

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- formato

def numero(valor, decimales: int = 0) -> str:
    """1234.5 -> '1.234,5' (como se escribe en castellano); un NaN -> '—'."""
    if valor is None or pd.isna(valor):
        return "—"
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def porcentaje(valor, decimales: int = 1) -> str:
    """12.34 -> '12,3 %'."""
    texto = numero(valor, decimales)
    return texto if texto == "—" else f"{texto} %"


def fecha(valor) -> str:
    """Timestamp -> '02-09-2020'."""
    return "—" if pd.isna(valor) else f"{pd.Timestamp(valor):%d-%m-%Y}"


def tabla(cabecera: list[str], filas: list[list]) -> str:
    """Tabla en Markdown."""
    lineas = ["| " + " | ".join(cabecera) + " |", "|" + " --- |" * len(cabecera)]
    lineas += ["| " + " | ".join(str(celda) for celda in fila) + " |" for fila in filas]
    return "\n".join(lineas)


# ---------------------------------------------------------------- cifras

def agrupar_descartadas(crudo: pd.DataFrame) -> dict[str, list[str]]:
    """Columnas del original que la limpieza no conserva, agrupadas por el motivo."""
    descartadas = [columna for columna in crudo.columns if columna not in COLUMNAS]
    vacias = [c for c in descartadas if crudo[c].isna().all()]
    ceros = [c for c in descartadas if c not in vacias and crudo[c].eq(0).all()]
    ya = set(vacias + ceros + REPETIDAS + METADATOS)
    return {
        "Vacías al 100 %": vacias,
        "Siempre valen 0 (la fuente las daba por obsoletas)": ceros,
        "Repiten otra columna": [c for c in REPETIDAS if c in descartadas],
        "Metadatos de la API (cuándo se actualizó el registro)": [
            c for c in METADATOS if c in descartadas],
        "Demasiados nulos o una unidad distinta en cada estado": [
            c for c in descartadas if c not in ya],
    }


def nulos_por_posicion(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Nulos de cada columna: antes del primer dato de cada estado o después de empezar."""
    ordenado = df.sort_values(["estado", "fecha"])
    filas = []
    for columna in columnas:
        nulo = ordenado[columna].isna()
        empezado = ordenado[columna].notna().astype(int).groupby(ordenado["estado"]).cummax() == 1
        filas.append({
            "columna": columna,
            "nulos": int(nulo.sum()),
            "nulos_pct": nulo.mean() * 100,
            "antes_del_primer_dato": int((nulo & ~empezado).sum()),
            "despues_de_empezar": int((nulo & empezado).sum()),
        })
    return pd.DataFrame(filas).set_index("columna")


def peso_atrasos(limpio: pd.DataFrame) -> pd.DataFrame:
    """Días marcados como atraso y qué parte del total de la columna suman."""
    filas = []
    for columna, marca in COLUMNAS_ATRASO.items():
        marcados = limpio[marca]
        filas.append({
            "marca": marca,
            "columna": columna,
            "filas": int(marcados.sum()),
            "estados": limpio.loc[marcados, "estado"].nunique(),
            "pct_del_total": limpio.loc[marcados, columna].sum() / limpio[columna].sum() * 100,
        })
    return pd.DataFrame(filas).set_index("marca")


def cobertura_mensual(df: pd.DataFrame, columna: str, meses: list[str]) -> pd.Series:
    """% de días-estado (50 estados y DC) con dato en `columna`, en cada mes pedido."""
    estados = df[~df["es_territorio"]]
    por_mes = estados[columna].notna().groupby(estados["fecha"].dt.strftime("%Y-%m")).mean() * 100
    return por_mes.reindex(meses)


def calcular_cifras(crudo: pd.DataFrame, censo: pd.DataFrame) -> dict:
    """Todas las cifras del informe, a partir de los dos originales."""
    original = marcar_territorios(seleccionar_y_renombrar(convertir_fecha(crudo)))
    tablas = preparar_datos(crudo, censo)
    limpio, final = tablas["limpio"], tablas["final"]

    marcas = revisar_coherencia(original)
    descripciones = {nombre: texto for nombre, (texto, _) in REGLAS_COHERENCIA.items()}
    ceros = final[final["cero_sin_publicar"]]
    ceros_estados = ceros[~ceros["es_territorio"]]

    oh, desde, hasta = VOLCADO_VARIOS_DIAS
    volcado = limpio[(limpio["estado"] == oh) & limpio["fecha"].between(desde, hasta)]

    ultimo = final.sort_values("fecha").groupby("estado").tail(1)
    return {
        "filas": len(crudo),
        "columnas": crudo.shape[1],
        "n_estados": crudo["state"].nunique(),
        "desde": original["fecha"].min(),
        "hasta": original["fecha"].max(),
        "nulos_original": crudo.isna().mean() * 100,
        "descartadas": agrupar_descartadas(crudo),
        "duplicados": int(crudo.duplicated(["date", "state"]).sum()),
        "nulos_conservadas": nulos_por_posicion(original, list(COLUMNAS.values())),
        "cobertura_hospital": cobertura_mensual(original, "hospitalizados_actuales",
                                                MESES_COBERTURA),
        "correcciones": resumir_correcciones(original, COLUMNAS_INCREMENTO),
        "filas_correccion": int(limpio["es_correccion"].sum()),
        "diferencia_totales": diferencia_totales(limpio[~limpio["es_territorio"]]),
        "coherencia": resumir_marcas(original, marcas, descripciones),
        "positividad_antes": int((positividad_7d(tablas["variables"], maximo=None) > 1).sum()),
        "positividad_despues": int((positividad_7d(final, maximo=None) > 1).sum()),
        "atrasos": peso_atrasos(limpio),
        "volcado": volcado[["fecha", "muertes_nuevas", "atraso_muertes"]],
        "ceros": len(ceros),
        "ceros_estados": len(ceros_estados),
        "ceros_n_estados": ceros_estados["estado"].nunique(),
        "ceros_fin_de_semana": (ceros_estados["fecha"].dt.day_of_week >= 5).mean() * 100,
        "sin_poblacion": sorted(final.loc[final["poblacion"].isna(), "estado"].unique()),
        "filas_sin_poblacion": int(final["poblacion"].isna().sum()),
        "fuentes_tests": ultimo["fuente_tests"].value_counts(),
    }


# ---------------------------------------------------------------- texto

def seccion_faltantes(c: dict) -> str:
    """1. Qué faltaba: columnas descartadas, nulos de las conservadas y duplicados."""
    nulos = c["nulos_original"]
    descartadas = c["descartadas"]
    n_descartadas = sum(len(columnas) for columnas in descartadas.values())
    filas_descartadas = [[motivo, len(columnas), ", ".join(f"`{x}`" for x in columnas)]
                         for motivo, columnas in descartadas.items() if columnas]

    filas_nulos = []
    for columna, fila in c["nulos_conservadas"].iterrows():
        filas_nulos.append([
            f"`{columna}`", porcentaje(fila["nulos_pct"]), numero(fila["antes_del_primer_dato"]),
            numero(fila["despues_de_empezar"]),
            DECISION_NULOS.get(columna, "—") if fila["nulos"] else "Sin nulos",
        ])

    texto = [
        "## 1. Qué faltaba",
        "",
        "### 1.1 Columnas descartadas",
        "",
        f"El original tiene {c['columnas']} columnas. **{numero((nulos > 50).sum())} están "
        f"vacías en más de la mitad de las filas** y {numero((nulos == 100).sum())} no tienen "
        "ningún dato. No es un error de descarga: cada estado publicaba cosas distintas. "
        f"Se conservan {c['columnas'] - n_descartadas} columnas y se descartan {n_descartadas}:",
        "",
        tabla(["Motivo", "Columnas", "Cuáles"], filas_descartadas),
        "",
        "Ninguna se imputa: en las columnas con más de la mitad de nulos habría que inventar "
        "más datos de los que hay. Del desglose de tests basta con `totalTestResults`, que ya "
        "junta los tests de cada estado, y `totalTestResultsSource`, que dice en qué unidad "
        "los contaba.",
        "",
        "### 1.2 Nulos en las columnas que se conservan",
        "",
        "Para cada columna, cuántos nulos caen **antes del primer dato** de cada estado (aún no "
        "publicaba, o no lo publicó nunca) y cuántos **después de empezar** (huecos o series que "
        "se cortan).",
        "",
        tabla(["Columna", "% nulos", "Antes del primer dato", "Después de empezar", "Decisión"],
              filas_nulos),
        "",
        "- En los acumulados, casi todos los nulos están antes del primer dato: significan «aún no "
        "se publicaba», no «cero». Imputar con la media o la mediana no tiene sentido en una cifra "
        "que crece cada día, y un 0 falsearía el inicio de la serie.",
    ]
    cobertura = c["cobertura_hospital"]
    if cobertura.notna().any():
        meses = ", ".join(f"{porcentaje(valor, 0)} en {mes}" for mes, valor in cobertura.items()
                          if pd.notna(valor))
        texto.append(
            "- Los hospitalizados se empezaron a publicar tarde. Días-estado con dato "
            f"(50 estados y DC): {meses}. Por eso **la cifra nacional de la primavera de 2020 "
            "se queda corta**.")
    texto += [
        "",
        "### 1.3 Duplicados",
        "",
        f"Filas repetidas del mismo estado y día: **{numero(c['duplicados'])}**. No hay nada que "
        "eliminar.",
    ]
    return "\n".join(texto)


def seccion_correcciones(c: dict) -> str:
    """2. Qué se corrigió y qué impacto tiene."""
    correcciones = c["correcciones"]
    coherencia = c["coherencia"]
    imposibles = coherencia.loc["positivos_sobre_tests"]
    diferencia = c["diferencia_totales"]["diferencia_pct"]

    filas_resumen = [
        ["Incrementos diarios negativos (correcciones del estado)", numero(c["filas_correccion"]),
         "El valor negativo pasa a `NaN` y la fila se marca en `es_correccion`",
         f"La suma de incrementos supera al acumulado oficial en un "
         f"{porcentaje(diferencia.get('casos_nuevos'), 2)} en casos y un "
         f"{porcentaje(diferencia.get('muertes_nuevas'), 2)} en muertes"],
        ["Más positivos acumulados que tests", numero(imposibles["filas"]),
         "Los tests de la fila pasan a `NaN` y se marca en `positivos_sobre_tests`",
         f"La positividad por encima del 100 % baja de {numero(c['positividad_antes'])} "
         f"a {numero(c['positividad_despues'])} valores"],
        ["Positividad de 7 días por encima del 100 %", numero(c["positividad_despues"]),
         "Pasa a `NaN` (no es posible)",
         "Son semanas en las que casi no se publicaron tests"],
    ]
    filas_detalle = [
        [f"`{columna}`", numero(fila["correcciones"]), numero(fila["estados"]),
         numero(fila["total_restado"]),
         f"{numero(fila['mayor'])} ({fila['mayor_estado']}, {fecha(fila['mayor_fecha'])})"]
        for columna, fila in correcciones.iterrows()
    ]
    filas_totales = [
        [f"`{incremento}`", numero(fila["suma_incrementos"]), numero(fila["ultimo_acumulado"]),
         porcentaje(fila["diferencia_pct"], 2)]
        for incremento, fila in c["diferencia_totales"].iterrows()
    ]
    return "\n".join([
        "## 2. Qué se corrigió",
        "",
        tabla(["Problema", "Filas", "Corrección", "Impacto"], filas_resumen),
        "",
        "### 2.1 Incrementos negativos",
        "",
        "Un estado no puede tener «casos nuevos negativos»: son días en que restó de golpe "
        "duplicados o errores de días anteriores. El incremento de cada día es exactamente la "
        "diferencia entre dos acumulados seguidos, así que estos días son los días en que el "
        "acumulado baja. No se pone un 0 (no sabemos cuántos casos hubo ese día) ni se borra la "
        "fila (el resto de sus columnas son válidas). Los acumulados no se tocan: ya incluyen la "
        "corrección.",
        "",
        tabla(["Columna", "Correcciones", "Estados", "Total restado", "La mayor"], filas_detalle),
        "",
        "Al quitar las restas, la suma de los incrementos queda algo por encima del último "
        "acumulado oficial (50 estados y DC):",
        "",
        tabla(["Incremento", "Suma de incrementos", "Último acumulado", "Diferencia"],
              filas_totales),
        "",
        "### 2.2 Más positivos que tests",
        "",
        f"Son {numero(imposibles['filas'])} filas de {numero(imposibles['estados'])} estados "
        f"({imposibles['principales']}), entre el {fecha(imposibles['desde'])} y el "
        f"{fecha(imposibles['hasta'])}: los primeros días de cada serie, cuando los estados "
        "publicaban los positivos antes que todos sus tests. La cifra de tests de esas filas está "
        "incompleta, así que pasa a `NaN`; los casos se conservan.",
    ])


def seccion_marcas(c: dict) -> str:
    """3. Qué se marcó sin cambiar el valor."""
    coherencia = c["coherencia"]
    filas = []
    for marca, fila in c["atrasos"].iterrows():
        filas.append([f"`{marca}`", numero(fila["filas"]), numero(fila["estados"]),
                      f"{porcentaje(fila['pct_del_total'])} de `{fila['columna']}`",
                      MOTIVO_MARCA[marca]])
    for marca in ["ventilador_sobre_uci", "recuperados_sobre_casos"]:
        fila = coherencia.loc[marca]
        filas.append([f"`{marca}`", numero(fila["filas"]), numero(fila["estados"]),
                      fila["principales"], MOTIVO_MARCA[marca]])
    filas.append(["`cero_sin_publicar`", numero(c["ceros"]), numero(c["ceros_n_estados"]),
                  f"{porcentaje(c['ceros_fin_de_semana'], 0)} en fin de semana",
                  MOTIVO_MARCA["cero_sin_publicar"]])
    sin_problema = coherencia.loc[coherencia["filas"] == 0, "descripcion"]
    texto = [
        "## 3. Qué se marcó sin cambiar el valor",
        "",
        "Hay datos dudosos que no son errores, o que están en columnas que no se usan en las "
        "conclusiones. Se dejan como están y se añade una columna booleana para poder separarlos.",
        "",
        tabla(["Marca", "Filas", "Estados", "Detalle", "Por qué no se corrige"], filas),
        "",
        "- **Atrasos:** días que multiplican por 5 o más la media de sus vecinos y son atípicos "
        "dentro de su estado: un estado que publica de golpe registros de semanas anteriores.",
        f"- **Días sin publicar:** días con 0 casos en estados que ya llevaban más de 1.000; "
        f"{numero(c['ceros_estados'])} son de los 50 estados y DC y el resto de los territorios.",
    ]
    if len(sin_problema):
        texto.append(f"- Reglas de coherencia que no fallan en ninguna fila ({len(sin_problema)}): "
                     + ", ".join(f"«{regla}»" for regla in sin_problema) + ".")
    return "\n".join(texto)


def seccion_pendiente(c: dict) -> str:
    """4. Qué quedó pendiente y por qué."""
    nulos = c["nulos_conservadas"]["nulos_pct"]
    referencia = nulos.reindex(["uci_actuales", "ventilador_actuales", "recuperados"])
    fuentes = c["fuentes_tests"]
    volcado = c["volcado"]
    texto = [
        "## 4. Qué quedó pendiente y por qué",
        "",
        f"- **Tests contados en unidades distintas.** Al cierre, los estados usaban "
        f"{numero(len(fuentes))} unidades distintas ("
        + ", ".join(f"`{fuente}` en {numero(n)}" for fuente, n in fuentes.items())
        + "). No se pueden convertir unas en otras con estos datos: la positividad sirve para ver "
        "la tendencia de un estado, pero las comparaciones entre estados son aproximadas.",
        f"- **Hospitalizados incompletos al principio.** `hospitalizados_actuales` tiene un "
        f"{porcentaje(nulos.get('hospitalizados_actuales'))} de nulos, sobre todo en la primavera "
        "de 2020. No se pueden reconstruir los días en que un estado aún no lo publicaba; al "
        "interpretar esa época hay que tener en cuenta que la cifra nacional se queda corta.",
        f"- **UCI, respirador y recuperados.** Entre un {porcentaje(referencia.min(), 0)} y un "
        f"{porcentaje(referencia.max(), 0)} de nulos y definiciones distintas en cada estado: "
        "se conservan como referencia, sin sacar conclusiones de ellas.",
    ]
    if len(volcado) and volcado["atraso_muertes"].any():
        dias = ", ".join(f"{numero(fila['muertes_nuevas'])} el {fecha(fila['fecha'])}"
                         + (" (marcado)" if fila["atraso_muertes"] else "")
                         for _, fila in volcado.iterrows())
        texto.append(
            "- **Atrasos que duran varios días.** El criterio solo detecta los volcados más "
            f"claros: Ohio sumó {dias}. Los días de alrededor no salen marcados porque su media de "
            "vecinos ya incluye el pico. Por eso las series temporales usan la media de 7 días, "
            "que amortigua también los que se escapan.")
    texto += [
        "- **Totales a partir de incrementos.** Por las correcciones quitadas, la suma de los "
        "incrementos queda algo por encima del acumulado oficial (apartado 2.1). Para la cifra "
        "oficial exacta de un estado hay que usar su último acumulado.",
    ]
    if c["sin_poblacion"]:
        texto.append(
            f"- **Territorios sin población.** {', '.join(c['sin_poblacion'])} no están en la "
            f"tabla del US Census Bureau: sus {numero(c['filas_sin_poblacion'])} filas no tienen "
            "tasas por 100.000 habitantes. Las comparaciones por habitante se hacen con los 50 "
            "estados, DC y Puerto Rico.")
    texto.append(
        "- **Casos sin detectar en la primera ola.** En la primavera de 2020 se hacían muy pocos "
        "tests y solo se detectaban los casos graves. Con estos datos no se puede estimar cuántos "
        "casos reales hubo, así que las comparaciones de casos entre olas se interpretan con "
        "cuidado (las muertes son más comparables).")
    return "\n".join(texto)


def redactar(c: dict) -> str:
    """El informe completo en Markdown."""
    atrasos = c["atrasos"]
    coherencia = c["coherencia"]
    n_descartadas = sum(len(columnas) for columnas in c["descartadas"].values())
    diferencia = c["diferencia_totales"]["diferencia_pct"]
    incoherentes = coherencia.loc[["ventilador_sobre_uci", "recuperados_sobre_casos"],
                                  "filas"].sum()
    resumen = [
        f"- **Qué faltaba:** se descartan {n_descartadas} de las {c['columnas']} columnas: vacías, "
        "constantes, repetidas, metadatos o con demasiados nulos. En las que se conservan, los "
        "nulos están casi siempre antes de que cada estado empezara a publicar y no se imputan.",
        f"- **Qué se corrigió:** {numero(c['filas_correccion'])} incrementos negativos pasan a "
        f"`NaN` y los tests de {numero(coherencia.loc['positivos_sobre_tests', 'filas'])} filas "
        "con más positivos que tests también. Los totales cambian un "
        f"{porcentaje(diferencia.get('casos_nuevos'), 2)} en casos y un "
        f"{porcentaje(diferencia.get('muertes_nuevas'), 2)} en muertes.",
        f"- **Qué se marcó:** {numero(atrasos['filas'].sum())} atrasos de notificación, "
        f"{numero(c['ceros'])} días sin publicar y "
        f"{numero(incoherentes)} filas incoherentes en columnas que no se usan.",
        "- **Qué quedó pendiente:** las unidades distintas de los tests, los hospitalizados de la "
        "primavera de 2020 y los atrasos de varios días seguidos. Se explica por qué en el "
        "apartado 4.",
    ]
    partes = [
        "# Informe de calidad de datos",
        "",
        f"**Datos:** The COVID Tracking Project, una fila por estado y día: "
        f"{numero(c['filas'])} filas y {c['columnas']} columnas de {c['n_estados']} estados y "
        f"territorios, del {fecha(c['desde'])} al {fecha(c['hasta'])}.",
        "",
        "Este informe recoge qué faltaba en los datos, qué se corrigió y qué quedó pendiente. "
        "Todas las cifras se calculan con `python -m src.informe_calidad` a partir de los "
        "originales; el detalle de cada decisión está en los notebooks 01, 02 y 06.",
        "",
        "## Resumen",
        "",
        "\n".join(resumen),
        "",
        seccion_faltantes(c),
        "",
        seccion_correcciones(c),
        "",
        seccion_marcas(c),
        "",
        seccion_pendiente(c),
        "",
    ]
    return "\n".join(partes)


def generar(raw: Path = CARPETA_RAW, salida: Path = RUTA_INFORME) -> Path:
    """Calcula las cifras, escribe el informe y devuelve su ruta."""
    crudo = cargar_datos(Path(raw) / ORIGINALES["covid"])
    censo = cargar_poblacion(Path(raw) / ORIGINALES["censo"])
    texto = redactar(calcular_cifras(crudo, censo))
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto, encoding="utf-8")
    return salida


def main() -> None:
    """Punto de entrada de `python -m src.informe_calidad`."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ruta = generar()
    log.info("Guardado %s", ruta)


if __name__ == "__main__":
    main()
