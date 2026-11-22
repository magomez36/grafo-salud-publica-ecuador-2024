
# Validacion adicional de las fuentes INEC y MSP 2024
# Instalar una sola vez: pip install pandas

from pathlib import Path
from collections import Counter
import json
import re
import unicodedata
import pandas as pd

# Configuracion
CARPETA = Path(__file__).resolve().parent.parent
SALIDA = CARPETA / "resultados_validacion"
BLOQUE = 100000
FUENTES = {
    "INEC": {
        "archivo": "egresos_hospitalarios_2024.csv",
        "cie": "cau_cie10", "provincia": "prov_ubi",
        "canton": "cant_ubi", "fecha": "fecha_egr",
        "extra": ["causa3"],
    },
    "MSP": {
        "archivo": "MSP_Emergencias_2024.csv",
        "cie": "CIE", "provincia": "PROVINCIA",
        "canton": "CANTON", "fecha": "FECHA_DE_ATENCION",
        "extra": [],
    },
}

# Normalizacion de nombres y codigos
def normalizar(texto):
    texto = unicodedata.normalize(
        "NFKD", str(texto).upper().strip()
    )
    texto = "".join(
        c for c in texto if not unicodedata.combining(c)
    )
    return re.sub(
        r"\s+", " ",
        re.sub(r"[^A-Z0-9 ]", " ", texto)
    ).strip()


def normalizar_serie(serie):
    equivalencias = {
        v: normalizar(v) for v in serie.unique()
    }
    return serie.map(equivalencias)


def codigo_cie(serie):
    # INEC: "J189 Neumonia..."; MSP: "J189"
    return (
        serie.astype(str)
        .str.strip()
        .str.upper()
        .str.extract(
            r"^([A-Z][0-9]{2}[A-Z0-9]{0,4})(?=\s|$|[.,;])",
            expand=False
        )
    )


def acumular(contador, conteos):
    contador.update({
        k: int(n) for k, n in conteos.items()
    })


def exportar(nombre, filas, columnas):
    pd.DataFrame(
        filas, columns=columnas
    ).to_csv(
        SALIDA / nombre,
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )


# Lectura por bloques y recuentos
def explorar(nombre, cfg):
    ruta = CARPETA / cfg["archivo"]

    if not ruta.is_file():
        raise FileNotFoundError(
            f"No se encontro: {ruta}"
        )

    conteo_cie3 = Counter()
    conteo_provincias = Counter()
    conteo_provincia_mes = Counter()
    conteo_cantones = Counter()
    resumen = Counter()

    columnas = [
        cfg["cie"],
        cfg["provincia"],
        cfg["canton"],
        cfg["fecha"],
        *cfg["extra"]
    ]

    for bloque in pd.read_csv(
        ruta,
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
        usecols=columnas,
        chunksize=BLOQUE,
        on_bad_lines="error",
    ):
        resumen["registros"] += len(bloque)

        # Diagnosticos: separar el codigo de su descripcion
        completo = codigo_cie(
            bloque[cfg["cie"]]
        )
        cie3 = completo.str[:3]

        resumen["cie_no_identificado"] += int(
            cie3.isna().sum()
        )

        acumular(
            conteo_cie3,
            cie3.dropna().value_counts()
        )

        if nombre == "INEC":
            # Comprobar coherencia con causa3
            causa3 = codigo_cie(
                bloque["causa3"]
            ).str[:3]

            comparables = (
                cie3.notna() & causa3.notna()
            )

            resumen["cie3_comparables"] += int(
                comparables.sum()
            )

            resumen[
                "cie3_discrepancias_con_causa3"
            ] += int(
                (
                    cie3.loc[comparables]
                    != causa3.loc[comparables]
                ).sum()
            )

        # Normalizacion de provincias y cantones
        provincia = normalizar_serie(
            bloque[cfg["provincia"]]
        )
        canton = normalizar_serie(
            bloque[cfg["canton"]]
        )

        acumular(
            conteo_provincias,
            provincia.value_counts()
        )

        pares = pd.DataFrame({
            "p": provincia,
            "c": canton
        })

        acumular(
            conteo_cantones,
            pares.value_counts()
        )

        # Cobertura por provincia y mes
        fecha = pd.to_datetime(
            bloque[cfg["fecha"]],
            format="%Y-%m-%d",
            errors="coerce"
        )

        resumen["fechas_invalidas"] += int(
            fecha.isna().sum()
        )

        resumen["fechas_fuera_de_2024"] += int(
            (
                fecha.notna()
                & (fecha.dt.year != 2024)
            ).sum()
        )

        meses = fecha.dt.strftime("%Y-%m")

        pares_mes = pd.DataFrame({
            "p": provincia,
            "mes": meses
        }).dropna()

        acumular(
            conteo_provincia_mes,
            pares_mes.value_counts()
        )

    resumen["codigos_cie3_distintos"] = len(
        conteo_cie3
    )
    resumen["provincias_distintas"] = len(
        conteo_provincias
    )
    resumen["estratos_provincia_mes"] = len(
        conteo_provincia_mes
    )

    exportar(
        f"cie3_corregido_{nombre.lower()}.csv",
        conteo_cie3.most_common(),
        ["codigo_cie3", "registros"]
    )

    return {
        "resumen": dict(resumen),
        "cie3": conteo_cie3,
        "provincias": conteo_provincias,
        "provincia_mes": conteo_provincia_mes,
        "cantones": conteo_cantones
    }


# Comparacion entre las dos fuentes
def main():
    SALIDA.mkdir(exist_ok=True)
    datos = {}

    for nombre, cfg in FUENTES.items():
        datos[nombre] = explorar(
            nombre, cfg
        )
        print(
            f"{nombre}: analisis completado"
        )

    a = datos["INEC"]
    b = datos["MSP"]

    comunes = (
        set(a["cie3"])
        & set(b["cie3"])
    )

    prov_comunes = (
        set(a["provincias"])
        & set(b["provincias"])
    )

    pm_comunes = (
        set(a["provincia_mes"])
        & set(b["provincia_mes"])
    )

    canton_comunes = (
        set(a["cantones"])
        & set(b["cantones"])
    )

    exportar(
        "cie3_compartidos_corregidos.csv",
        sorted(
            [
                (
                    k,
                    a["cie3"][k],
                    b["cie3"][k]
                )
                for k in comunes
            ],
            key=lambda x: min(x[1], x[2]),
            reverse=True
        ),
        [
            "codigo_cie3",
            "registros_inec",
            "registros_msp"
        ]
    )

    exportar(
        "cobertura_provincia_mes.csv",
        sorted([
            (
                p,
                m,
                a["provincia_mes"].get(
                    (p, m), 0
                ),
                b["provincia_mes"].get(
                    (p, m), 0
                )
            )
            for p, m in (
                set(a["provincia_mes"])
                | set(b["provincia_mes"])
            )
        ]),
        [
            "provincia",
            "mes",
            "registros_inec",
            "registros_msp"
        ]
    )

    resumen = {
        "INEC": a["resumen"],
        "MSP": b["resumen"],
        "comparacion": {
            "cie3_compartidos": len(
                comunes
            ),
            "provincias_compartidas": len(
                prov_comunes
            ),
            "estratos_provincia_mes_compartidos": len(
                pm_comunes
            ),
            "pares_provincia_canton_coincidentes": len(
                canton_comunes
            )
        }
    }

    (
        SALIDA / "resumen_validacion.json"
    ).write_text(
        json.dumps(
            resumen,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        "CIE-10 de tres caracteres compartidos:",
        len(comunes)
    )
    print(
        "Provincias compartidas:",
        len(prov_comunes)
    )
    print(
        f"Resultados: {SALIDA}"
    )


if __name__ == "__main__":
    main()
