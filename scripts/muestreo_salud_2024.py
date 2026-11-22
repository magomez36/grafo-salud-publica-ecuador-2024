# Muestreo estratificado para el grafo de salud publica de Ecuador, 2024
# Requiere Python 3 y resultados_validacion/cobertura_provincia_mes.csv.
# No necesita librerias externas.

from collections import Counter
from datetime import datetime
from pathlib import Path
import csv
import json
import random
import re
import unicodedata

# Configuracion
CARPETA = Path(__file__).resolve().parent.parent
SALIDA = CARPETA / 'datos_muestreados'
COBERTURA = CARPETA / 'resultados_validacion' / 'cobertura_provincia_mes.csv'
TAMANO_MUESTRA = 2592
MINIMO_POR_ESTRATO = 2
SEMILLA = 20241121

FUENTES = {
    'INEC': {
        'archivo': 'egresos_hospitalarios_2024.csv',
        'provincia': 'prov_ubi', 'fecha': 'fecha_egr',
        'cie': 'cau_cie10', 'conteo': 'registros_inec',
    },
    'MSP': {
        'archivo': 'MSP_Emergencias_2024.csv',
        'provincia': 'PROVINCIA', 'fecha': 'FECHA_DE_ATENCION',
        'cie': 'CIE', 'conteo': 'registros_msp',
    },
}

# Normalizacion de la provincia y validacion temporal
def normalizar(valor):
    texto = unicodedata.normalize('NFKD', str(valor).strip())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[^A-Z0-9 ]+', ' ', texto.upper())
    return ' '.join(texto.split())


def obtener_mes(valor):
    try:
        fecha = datetime.strptime(valor.strip(), '%Y-%m-%d')
        return fecha.strftime('%Y-%m') if fecha.year == 2024 else None
    except (AttributeError, ValueError):
        return None


def cie3(valor):
    encontrado = re.match(r'^([A-Z][0-9]{2})', str(valor).strip().upper())
    return encontrado.group(1) if encontrado else None

# Lectura de los tamanos reales de los 288 estratos

def leer_cobertura():
    if not COBERTURA.is_file():
        raise FileNotFoundError(
            'Falta resultados_validacion/cobertura_provincia_mes.csv. '
            'Conserva la carpeta de la validacion ejecutada anteriormente.'
        )
    cobertura = {}
    with COBERTURA.open('r', encoding='utf-8-sig', newline='') as archivo:
        lector = csv.DictReader(archivo, delimiter=';')
        campos = {'provincia', 'mes', 'registros_inec', 'registros_msp'}
        if not campos.issubset(set(lector.fieldnames or [])):
            raise ValueError('El archivo de cobertura no contiene las cuatro columnas esperadas.')
        for f in lector:
            clave = (normalizar(f['provincia']), f['mes'].strip())
            if clave in cobertura:
                raise ValueError(f'Estrato repetido: {clave}')
            cobertura[clave] = {
                'INEC': int(f['registros_inec']),
                'MSP': int(f['registros_msp']),
            }
    if len(cobertura) != 288:
        raise ValueError(f'Se esperaban 288 provincia-mes, se encontraron {len(cobertura)}.')
    provincias = {k[0] for k in cobertura}
    if len(provincias) != 24 or len({k[1] for k in cobertura}) != 12:
        raise ValueError('La cobertura no tiene 24 provincias y los 12 meses de 2024.')
    return cobertura

# Calculo de cuotas reproducibles: minimo dos y resto proporcional

def asignar_cuotas(cobertura, nombre):
    grupos = sorted(cobertura)
    n = {grupo: cobertura[grupo][nombre] for grupo in grupos}
    if any(cantidad < MINIMO_POR_ESTRATO for cantidad in n.values()):
        raise ValueError(f'{nombre}: existe algun grupo sin cobertura minima.')
    disponibles = TAMANO_MUESTRA - len(grupos) * MINIMO_POR_ESTRATO
    if disponibles < 0:
        raise ValueError('El tamano de muestra no alcanza para cubrir los estratos.')
    total = sum(n.values())
    cuota = {grupo: MINIMO_POR_ESTRATO for grupo in grupos}
    exactos = {grupo: disponibles * n[grupo] / total for grupo in grupos}
    for grupo in grupos:
        cuota[grupo] += int(exactos[grupo])
    sobrantes = TAMANO_MUESTRA - sum(cuota.values())
    prioridad = sorted(grupos, key=lambda g: (-(exactos[g] - int(exactos[g])), g))
    for grupo in prioridad[:sobrantes]:
        cuota[grupo] += 1
    if sum(cuota.values()) != TAMANO_MUESTRA or any(cuota[g] > n[g] for g in grupos):
        raise ValueError(f'{nombre}: cuotas incompatibles con los datos originales.')
    return cuota

# Muestreo en una sola pasada sobre cada archivo grande

def muestrear(nombre, configuracion, cobertura, cuotas, semilla):
    ruta = CARPETA / configuracion['archivo']
    if not ruta.is_file():
        raise FileNotFoundError(f'No se encontro {ruta.name} junto al script.')
    generador = random.Random(semilla)
    observados = Counter()
    omitidos = Counter()
    reservas = {grupo: [] for grupo in cuotas}
    total = 0

    with ruta.open('r', encoding='utf-8-sig', newline='') as archivo:
        lector = csv.DictReader(archivo, delimiter=';')
        encabezados = lector.fieldnames
        requeridos = [configuracion['provincia'], configuracion['fecha'], configuracion['cie']]
        if not encabezados or any(c not in encabezados for c in requeridos):
            raise ValueError(f'Columnas obligatorias ausentes en {ruta.name}: {requeridos}')
        for numero, fila in enumerate(lector, start=1):
            total += 1
            provincia = normalizar(fila[configuracion['provincia']])
            mes = obtener_mes(fila[configuracion['fecha']])
            grupo = (provincia, mes)
            if grupo not in cuotas:
                omitidos['provincia_o_fecha_fuera_de_cobertura'] += 1
                continue
            observados[grupo] += 1
            fila['numero_fila_origen'] = str(numero)
            bolsa = reservas[grupo]
            k = cuotas[grupo]
            if len(bolsa) < k:
                bolsa.append(fila)
            else:
                posicion = generador.randrange(observados[grupo])
                if posicion < k:
                    bolsa[posicion] = fila

    diferencias = [g for g in cuotas if observados[g] != cobertura[g][nombre]]
    if diferencias:
        raise ValueError(
            f'{nombre}: el CSV y los conteos de validacion no coinciden '
            f'en {len(diferencias)} grupos; revisa los archivos de origen.'
        )

    seleccionados = [f for grupo in sorted(cuotas) for f in reservas[grupo]]
    seleccionados.sort(key=lambda f: int(f['numero_fila_origen']))
    salida = SALIDA / f'muestra_{nombre.lower()}_2024.csv'
    with salida.open('w', encoding='utf-8-sig', newline='') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=[*encabezados, 'numero_fila_origen'], delimiter=';')
        escritor.writeheader()
        escritor.writerows(seleccionados)

    codigos = {x for f in seleccionados if (x := cie3(f[configuracion['cie']]))}
    print(f'{nombre}: {total:,} registros examinados; {len(seleccionados):,} seleccionados.')
    return {
        'registros_originales': total,
        'registros_muestra': len(seleccionados),
        'estratos': len(cuotas),
        'cuota_minima': min(cuotas.values()),
        'cuota_maxima': max(cuotas.values()),
        'filas_fuera_de_cobertura': sum(omitidos.values()),
    }, codigos

# Exportar resumen, pesos y distribucion por provincia-mes

def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    cobertura = leer_cobertura()
    cuotas = {nombre: asignar_cuotas(cobertura, nombre) for nombre in FUENTES}
    resultados, codigos = {}, {}
    for i, (nombre, configuracion) in enumerate(FUENTES.items()):
        resultados[nombre], codigos[nombre] = muestrear(
            nombre, configuracion, cobertura, cuotas[nombre], SEMILLA + i
        )

    with (SALIDA / 'distribucion_muestras.csv').open('w', encoding='utf-8-sig', newline='') as archivo:
        escritor = csv.writer(archivo, delimiter=';')
        escritor.writerow(['provincia', 'mes', 'original_inec', 'original_msp',
                           'muestra_inec', 'muestra_msp', 'peso_inec', 'peso_msp'])
        for grupo in sorted(cobertura):
            ine = cobertura[grupo]['INEC']; msp = cobertura[grupo]['MSP']
            n_ine = cuotas['INEC'][grupo]; n_msp = cuotas['MSP'][grupo]
            escritor.writerow([grupo[0], grupo[1], ine, msp, n_ine, n_msp,
                               round(ine / n_ine, 6), round(msp / n_msp, 6)])

    resumen = {
        'metodo': 'muestreo aleatorio estratificado con minimo y asignacion adicional proporcional',
        'estratos': '24 provincias x 12 meses por fuente',
        'tamano_por_fuente': TAMANO_MUESTRA,
        'cuota_minima_base_por_estrato': MINIMO_POR_ESTRATO,
        'semilla': SEMILLA,
        'fuentes': resultados,
        'cie3_compartidos_en_muestras': len(codigos['INEC'] & codigos['MSP']),
        'advertencia': 'Las frecuencias de muestras no son totales de poblacion. Los pesos se muestran como referencia metodologica.',
    }
    (SALIDA / 'resumen_muestreo.json').write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print('Categorias CIE-10 compartidas entre muestras:', resumen['cie3_compartidos_en_muestras'])
    print('Archivos generados en:', SALIDA)


if __name__ == '__main__':
    main()
