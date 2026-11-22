
# EDA de las fuentes INEC y MSP 2024 - Práctica bimestral 1C
# Instalar una vez: pip install pandas

from pathlib import Path
from collections import Counter
from datetime import datetime
import csv
import json
import re
import unicodedata
import pandas as pd

# Configuración
CARPETA = Path(__file__).resolve().parent.parent
SALIDA = CARPETA / "resultados_eda"

ARCHIVOS = {
    "INEC": "egresos_hospitalarios_2024.csv",
    "MSP": "MSP_Emergencias_2024.csv",
}

TAMANO_BLOQUE = 50000
FILAS_MUESTRA_POR_BLOQUE = 4
LIMITE_CATEGORIAS = 30000
LIMITE_TOP = 25

NULOS = {
    "", "NA", "N/A", "NULL", "NAN", "NONE",
    "SIN INFORMACION", "SIN INFORMACIÓN",
    "NO INFORMA", "NO INFORMADO", "NO DISPONIBLE",
    "NO REGISTRA", "NO REPORTADO",
    "S/I", "S/D", "-", "--",
}

CAMPOS = {
    "INEC": {
        "territorio": [
            "prov_ubi", "cant_ubi", "parr_ubi",
            "prov_res", "cant_res", "parr_res",
            "area_ubi", "area_res",
        ],
        "diagnostico": [
            "cau_cie10", "causa3", "cap221rx",
            "cau221rx", "cau298rx",
        ],
        "fecha": [
            "fecha_ingr", "fecha_egr",
            "anio_egr", "mes_egr", "dia_egr",
        ],
        "demografia": [
            "sexo", "edad", "cod_edad", "nac_pac", "etnia",
        ],
        "establecimiento": [
            "clase", "tipo", "entidad", "sector",
        ],
        "otros": [
            "dia_estad", "tipo_seg", "dis_pac",
            "mes_inv", "cod_pais", "nom_pais",
            "con_egrpa", "esp_egrpa",
        ],
    },
    "MSP": {
        "territorio": [
            "PROVINCIA", "CANTON", "PARROQUIA",
            "PROVINCIA_DOM",
        ],
        "diagnostico": [
            "CIE", "DIAGNOSTICO",
            "CONDICION_DIAGNOSTICO",
        ],
        "fecha": [
            "FECHA_DE_ATENCION",
        ],
        "demografia": [
            "SEXO", "EDAD", "CONDICION_EDAD",
            "NACIONALIDAD",
        ],
        "establecimiento": [
            "UNICODIGO", "ESTABLECIMIENTO",
            "ZONA", "DISTRITO",
        ],
    },
}

NUMERICOS = {
    "INEC": [
        "edad", "dia_estad", "anio_egr",
        "mes_egr", "dia_egr",
    ],
    "MSP": ["EDAD"],
}

FECHAS = {
    "INEC": ["fecha_ingr", "fecha_egr"],
    "MSP": ["FECHA_DE_ATENCION"],
}

CIE_PRINCIPAL = {
    "INEC": "cau_cie10",
    "MSP": "CIE",
}

FORMATOS_FECHA = {
    "YMD": ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"],
    "DMY": [
        "%d/%m/%Y", "%d-%m-%Y",
        "%d.%m.%Y", "%d/%m/%y",
    ],
    "MDY": [
        "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y",
    ],
}

# Funciones auxiliares
def clave(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    return re.sub(
        r"[^A-Z0-9]+", "_", texto.upper()
    ).strip("_")


def nulo(texto):
    return (
        clave(texto).replace("_", " ") in NULOS
        or str(texto).strip().upper() in NULOS
    )


def obtener_formato(ruta):
    with ruta.open("rb") as fh:
        inicio = fh.read(131072)

    codificacion = "utf-8-sig"

    try:
        texto = inicio.decode(codificacion)
    except UnicodeDecodeError:
        codificacion = "cp1252"
        try:
            texto = inicio.decode(codificacion)
        except UnicodeDecodeError:
            codificacion = "latin-1"
            texto = inicio.decode(codificacion)

    try:
        separador = csv.Sniffer().sniff(
            texto[:30000], delimiters=",;\t|"
        ).delimiter
    except csv.Error:
        cabecera = texto.splitlines()[0]
        separador = max(
            [",", ";", "\t", "|"],
            key=cabecera.count,
        )

    return codificacion, separador


def normalizar_cie(texto):
    if nulo(texto):
        return None

    valor = re.sub(
        r"[^A-Z0-9]", "", str(texto).upper()
    )

    if re.fullmatch(
        r"[A-Z][0-9]{2}[A-Z0-9]{0,4}", valor
    ):
        return valor

    return None


def evaluar_fecha(valor):
    valor = (
        str(valor).strip()
        .replace("T", " ")
        .split(" ")[0]
    )

    compatibles = {}

    for familia, formatos in FORMATOS_FECHA.items():
        for formato in formatos:
            try:
                compatibles[familia] = (
                    datetime.strptime(valor, formato)
                    .date().isoformat()
                )
                break
            except ValueError:
                pass

    return compatibles


def escribir_csv(ruta, filas, columnas):
    with ruta.open(
        "w", newline="", encoding="utf-8-sig"
    ) as fh:
        writer = csv.DictWriter(
            fh, fieldnames=columnas, delimiter=";"
        )
        writer.writeheader()
        writer.writerows(filas)


# Exploración de cada archivo
def procesar(nombre, ruta):
    codificacion, separador = obtener_formato(ruta)

    lector = pd.read_csv(
        ruta,
        sep=separador,
        encoding=codificacion,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        chunksize=TAMANO_BLOQUE,
        on_bad_lines="error",
        low_memory=False,
    )

    totales = Counter()
    vacios = Counter()
    conteos = {}
    truncados = set()
    num_stats = {}
    cie3 = Counter()
    cie_no_valido = 0
    duplicados_bloque = 0
    muestras = []
    columnas = None
    disponibles = {}

    for indice_bloque, bloque in enumerate(lector):

        # Identificar los campos
        if columnas is None:
            columnas = list(bloque.columns)

            mapa = {
                clave(col): col
                for col in columnas
            }

            for grupo, esperados in CAMPOS[nombre].items():
                disponibles[grupo] = {
                    e: mapa[clave(e)]
                    for e in esperados
                    if clave(e) in mapa
                }

            seleccionados = list(dict.fromkeys(
                col
                for grupo in disponibles.values()
                for col in grupo.values()
            ))

            conteos = {
                col: Counter()
                for col in seleccionados
            }

            numericos = [
                mapa[clave(e)]
                for e in NUMERICOS[nombre]
                if clave(e) in mapa
            ]

            fechas = [
                mapa[clave(e)]
                for e in FECHAS[nombre]
                if clave(e) in mapa
            ]

            campo_cie = mapa.get(
                clave(CIE_PRINCIPAL[nombre])
            )

            num_stats = {
                col: {
                    "observados": 0,
                    "no_numericos": 0,
                    "negativos": 0,
                    "fraccionarios": 0,
                    "minimo": None,
                    "maximo": None,
                }
                for col in numericos
            }

        totales["filas"] += len(bloque)
        totales["bloques"] += 1

        # Duplicados detectados dentro de cada bloque
        duplicados_bloque += int(
            bloque.duplicated().sum()
        )

        # Valores faltantes y frecuencias
        for col in columnas:
            serie = bloque[col].astype(str).str.strip()
            faltante = serie.str.upper().isin(NULOS)

            vacios[col] += int(faltante.sum())

            if col in conteos:
                frecuencia = (
                    serie.loc[~faltante]
                    .value_counts(dropna=False)
                )

                conteos[col].update(
                    frecuencia.to_dict()
                )

                if len(conteos[col]) > LIMITE_CATEGORIAS:
                    conteos[col] = Counter(dict(
                        conteos[col].most_common(
                            LIMITE_CATEGORIAS // 2
                        )
                    ))
                    truncados.add(col)

        # Categorías CIE-10 comparables
        if campo_cie:
            valores = (
                bloque[campo_cie]
                .astype(str)
                .str.strip()
                .value_counts()
            )

            for valor, cantidad in valores.items():
                codigo = normalizar_cie(valor)

                if codigo:
                    cie3[codigo[:3]] += int(cantidad)
                else:
                    cie_no_valido += int(cantidad)

        # Validación exploratoria de datos numéricos
        for col in numericos:
            original = (
                bloque[col].astype(str).str.strip()
            )

            presente = ~original.str.upper().isin(
                NULOS
            )

            valores = pd.to_numeric(
                original.loc[presente].str.replace(
                    ",", ".", regex=False
                ),
                errors="coerce",
            )

            st = num_stats[col]
            st["observados"] += int(presente.sum())
            st["no_numericos"] += int(
                valores.isna().sum()
            )

            validos = valores.dropna()

            if not validos.empty:
                st["negativos"] += int(
                    (validos < 0).sum()
                )
                st["fraccionarios"] += int(
                    (validos != validos.round()).sum()
                )

                mn = float(validos.min())
                mx = float(validos.max())

                st["minimo"] = (
                    mn if st["minimo"] is None
                    else min(st["minimo"], mn)
                )
                st["maximo"] = (
                    mx if st["maximo"] is None
                    else max(st["maximo"], mx)
                )

        # Muestra pequeña para inspección
        if len(bloque):
            sub = bloque.sample(
                n=min(
                    FILAS_MUESTRA_POR_BLOQUE,
                    len(bloque),
                ),
                random_state=2024 + indice_bloque,
            ).copy()

            sub.insert(
                0,
                "numero_registro_csv",
                sub.index + 1,
            )
            muestras.append(sub)

    # Comprobaciones de lectura
    if columnas is None:
        raise ValueError(
            f"El archivo está vacío: {ruta.name}"
        )

    if len(columnas) < 3:
        raise ValueError(
            f"Se detectaron solo {len(columnas)} "
            f"columnas en {ruta.name}; "
            "revisa el separador."
        )

    # Reporte de calidad de columnas
    filas_columnas = [
        {
            "fuente": nombre,
            "columna": col,
            "filas": totales["filas"],
            "faltantes": vacios[col],
            "porcentaje_faltante": round(
                100 * vacios[col] /
                max(totales["filas"], 1), 3
            ),
            "valores_distintos_observados": (
                len(conteos[col])
                if col in conteos
                else "no calculado"
            ),
            "frecuencias_truncadas": (
                "SI" if col in truncados else "NO"
            ),
        }
        for col in columnas
    ]

    escribir_csv(
        SALIDA / f"columnas_{nombre.lower()}.csv",
        filas_columnas,
        list(filas_columnas[0].keys()),
    )

    # Reporte de categorías más frecuentes
    filas_frecuencia = []

    for grupo, correspondencia in disponibles.items():
        for col in correspondencia.values():
            for valor, cantidad in conteos[col].most_common(
                LIMITE_TOP
            ):
                filas_frecuencia.append({
                    "fuente": nombre,
                    "grupo": grupo,
                    "columna": col,
                    "valor": valor,
                    "frecuencia": int(cantidad),
                    "frecuencias_truncadas": (
                        "SI" if col in truncados else "NO"
                    ),
                })

    escribir_csv(
        SALIDA / f"frecuencias_{nombre.lower()}.csv",
        filas_frecuencia,
        [
            "fuente", "grupo", "columna",
            "valor", "frecuencia",
            "frecuencias_truncadas",
        ],
    )

    # Detección de formatos de fechas
    resumen_fechas = {}

    for col in fechas:
        resultado = Counter()
        ejemplos = []

        for valor, cantidad in conteos[col].items():
            opciones = evaluar_fecha(valor)

            if len(ejemplos) < 12:
                ejemplos.append({
                    "valor": valor,
                    "formatos_posibles": opciones,
                })

            if not opciones:
                resultado["no_interpretable"] += cantidad
            elif (
                "DMY" in opciones
                and "MDY" in opciones
            ):
                resultado["ambiguo_dia_mes"] += cantidad
            else:
                resultado[
                    "interpretable_sin_ambiguedad"
                ] += cantidad

            if opciones and all(
                fecha[:4] == "2024"
                for fecha in opciones.values()
            ):
                resultado["compatible_2024"] += cantidad

        resumen_fechas[col] = {
            "conteos": dict(resultado),
            "ejemplos": ejemplos,
            "frecuencias_truncadas": (
                col in truncados
            ),
        }

    # Identificar campos que no se encontraron
    presentes_normalizados = {
        clave(col) for col in columnas
    }

    no_encontrados = {
        grupo: [
            esperado
            for esperado in campos
            if clave(esperado)
            not in presentes_normalizados
        ]
        for grupo, campos in CAMPOS[nombre].items()
    }

    # Exportar muestra exploratoria
    muestra = pd.concat(
        muestras, ignore_index=True
    )

    muestra.to_csv(
        SALIDA /
        f"muestra_exploratoria_{nombre.lower()}.csv",
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )

    # Resumen general de la fuente
    resumen = {
        "fuente": nombre,
        "archivo": ruta.name,
        "tamano_gb": round(
            ruta.stat().st_size / 1024**3, 4
        ),
        "codificacion_probable": codificacion,
        "separador": repr(separador),
        "filas_leidas": int(totales["filas"]),
        "columnas_total": len(columnas),
        "columnas_originales": columnas,
        "campos_modelo_disponibles": disponibles,
        "campos_modelo_no_encontrados": no_encontrados,
        "columnas_frecuencias_truncadas": sorted(
            truncados
        ),
        "duplicados_exactos_dentro_de_bloques": (
            duplicados_bloque
        ),
        "advertencia_duplicados": (
            "Es un mínimo parcial y no demuestra "
            "registros clínicos repetidos. "
            "No eliminar automáticamente."
        ),
        "estadisticas_numericas": num_stats,
        "fechas": resumen_fechas,
        "cie3_codigos_distintos": len(cie3),
        "cie_registros_sin_codigo_valido": (
            cie_no_valido
        ),
        "nota": (
            "Los archivos originales no fueron "
            "modificados. Las muestras exploratorias "
            "no son la muestra RDF definitiva."
        ),
    }

    with (
        SALIDA / f"resumen_{nombre.lower()}.json"
    ).open("w", encoding="utf-8") as fh:
        json.dump(
            resumen,
            fh,
            ensure_ascii=False,
            indent=2,
        )

    # Exportar diagnósticos CIE-10 agrupados
    escribir_csv(
        SALIDA / f"cie3_{nombre.lower()}.csv",
        [
            {
                "codigo_cie3": codigo,
                "registros": n,
            }
            for codigo, n in cie3.most_common()
        ],
        ["codigo_cie3", "registros"],
    )

    print(
        f"{nombre}: {totales['filas']:,} registros "
        f"| {len(columnas)} columnas"
    )

    return resumen, cie3


# Ejecución del análisis
def main():
    SALIDA.mkdir(
        parents=True, exist_ok=True
    )

    resultados = {}
    codigos = {}

    for fuente, nombre_archivo in ARCHIVOS.items():
        ruta = CARPETA / nombre_archivo

        if not ruta.is_file():
            raise FileNotFoundError(
                f"No se encontró {ruta}. "
                "Coloca el .py junto a ambos CSV."
            )

        resultados[fuente], codigos[fuente] = (
            procesar(fuente, ruta)
        )

    # Comparar diagnósticos entre las fuentes
    compartidos = (
        set(codigos["INEC"])
        & set(codigos["MSP"])
    )

    coincidencias = [
        {
            "codigo_cie3": codigo,
            "egresos_inec": (
                codigos["INEC"][codigo]
            ),
            "emergencias_msp": (
                codigos["MSP"][codigo]
            ),
        }
        for codigo in compartidos
    ]

    coincidencias.sort(
        key=lambda x: min(
            x["egresos_inec"],
            x["emergencias_msp"],
        ),
        reverse=True,
    )

    escribir_csv(
        SALIDA / "coincidencias_cie3.csv",
        coincidencias,
        [
            "codigo_cie3",
            "egresos_inec",
            "emergencias_msp",
        ],
    )

    # Resumen comparativo
    with (
        SALIDA / "resumen_comparativo.json"
    ).open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "registros_inec": (
                    resultados["INEC"]["filas_leidas"]
                ),
                "registros_msp": (
                    resultados["MSP"]["filas_leidas"]
                ),
                "categorias_cie3_compartidas": (
                    len(compartidos)
                ),
                "observacion": (
                    "Compartir CIE-10 no permite "
                    "inferir vínculos individuales "
                    "entre pacientes."
                ),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "CIE-10 (tres caracteres) compartidos: "
        f"{len(compartidos)}"
    )
    print(f"Resultados guardados en: {SALIDA}")


if __name__ == "__main__":
    main()
