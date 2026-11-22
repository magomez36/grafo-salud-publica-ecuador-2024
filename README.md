# Grafo de conocimiento de salud pública en Ecuador (2024)

**Práctica bimestral 1 — Grupo 2**  
**Asignatura:** Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos

## Descripción y relación con las ciudades inteligentes

Proyecto académico de integración de datos sanitarios heterogéneos mediante **RDF, Turtle, SPARQL y GraphDB**. Reúne información oficial de **egresos hospitalarios del INEC** y **atenciones de emergencia del MSP** correspondiente al año **2024**.

El problema abordado es la dispersión de información sanitaria entre instituciones, que dificulta su exploración conjunta. Desde el enfoque de las **ciudades inteligentes**, el grafo permite consultar registros por territorio, diagnóstico y período, como apoyo potencial a futuros análisis de planificación de servicios de salud.

La integración se realiza por **provincia/cantón/parroquia, período mensual y categoría diagnóstica CIE-10**. **No se vinculan pacientes ni episodios individuales entre fuentes**, porque los archivos no contienen un identificador común que permita hacerlo de forma verificable.

## Objetivo y entregas

Diseñar e implementar un grafo de conocimiento que represente los registros sanitarios, sus atributos y las relaciones entre recursos, preservando la correspondencia con el modelo entidad-relación (MER) y el esquema RDF.

| Entrega | Alcance | Estado |
|---|---|---|
| **1A** | Definición del problema, dominio, preguntas de competencia y fuentes | Desarrollada |
| **1B** | Obtención y caracterización de datos; MER y esquema semántico RDF | Desarrollada |
| **1C** | Preparación y muestreo; generación de tripletas en R; carga y consultas en GraphDB | Implementada y verificada |

## Fuentes de datos

| Fuente | Archivo CSV original | Registros examinados | Variables |
|---|---|---:|---:|
| INEC — Egresos hospitalarios | `egresos_hospitalarios_2024.csv` | 1.132.667 | 38 |
| MSP — Atenciones de emergencia | `MSP_Emergencias_2024.csv` | 4.776.012 | 16 |
| **Total** | | **5.908.679** | |

**Fuentes oficiales:**

- [INEC — Camas y egresos hospitalarios](https://www.ecuadorencifras.gob.ec/camas-y-egresos-hospitalarios/)
- [INEC — Catálogo de metadatos 2024](https://anda.inec.gob.ec/anda5/index.php/catalog/1151)
- [MSP — Directorio de archivos de 2024](https://almacenamiento.msp.gob.ec/index.php/s/yDCA3vZfSgZZpJk?path=%2F2024)

Los archivos originales, de gran tamaño, **no se publican en este repositorio**. Se documentan sus fuentes oficiales y se incluyen muestras de trabajo. La disponibilidad pública de los datos no supone automáticamente autorización para redistribuirlos; cualquier publicación de muestras requiere revisar las condiciones de uso y los riesgos de privacidad.

## Preparación y tratamiento de los datos

El procedimiento se desarrolló en cuatro etapas, documentadas en los [scripts de procesamiento](scripts/):

1. **Exploración (`eda_fuentes_salud_2024.py`):** lectura por bloques de los CSV, inspección de columnas, fechas, valores faltantes, frecuencias y posibles duplicados. Las coincidencias exactas no se eliminaron automáticamente.
2. **Validación (`validacion_cie_territorio_2024.py`):** extracción y normalización de códigos CIE-10; estandarización de denominaciones geográficas y comprobación de períodos. En los archivos completos se identificaron **1.500 categorías CIE-10 de tres caracteres compartidas**, **24 provincias** y **288 combinaciones provincia-mes por fuente**.
3. **Muestreo (`muestreo_salud_2024.py`):** selección aleatoria estratificada por provincia y mes, con una cuota mínima de dos registros por estrato y asignación adicional proporcional. Se usó la semilla **`20241121`** y se conservó `numero_fila_origen` para la trazabilidad.
4. **Transformación RDF (`construccion_grafo_salud_2024.R`):** lectura de las muestras mediante `read.csv2()`, construcción de URI y tripletas con `rdf()` y `rdf_add()`, y exportación a Turtle con `rdf_serialize()`. La lectura posterior con `rdf_parse()` verificó la serialización.

**Muestras utilizadas:** 2.592 egresos del INEC y 2.592 atenciones del MSP (**5.184 registros sanitarios**). Ambas cubren las 24 provincias y los 12 meses de 2024; comparten **216 categorías CIE-10 de tres caracteres**.

> **Alcance:** las muestras permiten demostrar la integración y las consultas del grafo. Sus recuentos **no equivalen a los totales nacionales** y no deben interpretarse como estadísticas poblacionales sin considerar el diseño muestral.

## Modelo y resultados de la implementación

Se conservaron las **siete clases** del esquema diseñado en 1B: `Territorio`, `EstablecimientoSalud`, `DiagnosticoCIE10`, `Periodo`, `FuenteDatos`, `AtencionEmergencia` y `EgresoHospitalario`. El esquema define **12 propiedades de relación y 57 propiedades de datos**. Los diagnósticos detallados se vinculan a su categoría CIE-10 de tres caracteres mediante `skos:broader`, como extensión semántica documentada.

| Resultado | Cantidad verificada |
|---|---:|
| Egresos INEC representados | 2.592 |
| Atenciones MSP representadas | 2.592 |
| Recursos con tipo RDF | 8.109 |
| Tripletas de instancias — ABox | 138.227 |
| Tripletas de esquema — TBox | 249 |
| **Tripletas explícitas en GraphDB** | **138.476** |

Las cantidades se verificaron mediante la serialización/lectura RDF y consultas SPARQL en **GraphDB 11.5.3**. Las consultas de exploración demuestran, entre otros casos, que egresos del INEC y atenciones del MSP pueden compartir el recurso diagnóstico **`A049`**, sin implicar una relación individual entre esos registros.

## Estructura del proyecto

El repositorio organiza por separado los **datos preparados**, los **modelos de conocimiento**, los **scripts de procesamiento**, los **archivos RDF**, las **consultas SPARQL** y las **evidencias de GraphDB**:

```text
grafo-salud-publica-ecuador-2024/
├── README.md
├── datos_muestreados/
│   ├── muestra_inec_2024.csv
│   ├── muestra_msp_2024.csv
│   ├── distribucion_muestras.csv
│   └── resumen_muestreo.json
├── resultados_eda/
│   ├── resumen_inec.json
│   └── resumen_msp.json
├── resultados_validacion/
│   ├── resumen_validacion.json
│   ├── cobertura_provincia_mes.csv
│   └── cie3_compartidos_corregidos.csv
├── modelos/
│   ├── Modelo Entidad-Relación (MER).png
│   ├── Modelo Entidad-Relación (MER).drawio
│   ├── Esquema Semantico RDF - Salud Publica.png
│   └── Esquema Semantico RDF - Salud Publica.drawio
├── scripts/
│   ├── eda_fuentes_salud_2024.py
│   ├── validacion_cie_territorio_2024.py
│   ├── muestreo_salud_2024.py
│   └── construccion_grafo_salud_2024.R
├── rdf/
│   ├── esquema_semantico.ttl
│   └── instancias_salud_publica_2024.ttl
├── consultas/
│   ├── 01_total_tripletas.sparql
│   ├── 02_verificacion_clases.sparql
│   ├── 03_exploracion_emergencias.sparql
│   └── 04_integracion_inec_msp.sparql
└── evidencias/
    ├── 01_repositorio_graphdb.png
    ├── 02_importacion_turtle.png
    ├── 03_total_tripletas.png
    ├── 04_verificacion_clases.png
    ├── 05_consulta_atenciones.png
    ├── 06_grafo_atencion_msp.png
    ├── 07_consulta_integracion_a049.png
    ├── 08_grafo_egreso_inec.png
    ├── 09_grafo_integracion_a049.png
    └── 10_grafo_integracion_ampliado.png
```

**Flujo de trabajo:** fuentes CSV oficiales → exploración y validación en **Python** → muestras reproducibles → construcción de instancias con **R + `rdflib`** → archivos Turtle (esquema e instancias) → importación, consultas y visualización en **GraphDB**.

Los archivos originales del INEC y el MSP se conservan **fuera del repositorio** por su tamaño y por las precauciones de reutilización. Sus fuentes de descarga se indican arriba. Las carpetas y archivos mostrados corresponden a la **organización prevista de la entrega final**; los que aún no se hayan incorporado a `main` serán publicados por los integrantes responsables antes de la entrega.

## Archivos del proyecto

### Datos y resultados de procesamiento

| Recurso | Enlace |
|---|---|
| Muestra INEC | [muestra_inec_2024.csv](datos_muestreados/muestra_inec_2024.csv) |
| Muestra MSP | [muestra_msp_2024.csv](datos_muestreados/muestra_msp_2024.csv) |
| Distribución de las muestras | [distribucion_muestras.csv](datos_muestreados/distribucion_muestras.csv) |
| Resumen del muestreo | [resumen_muestreo.json](datos_muestreados/resumen_muestreo.json) |
| Resumen EDA INEC | [resumen_inec.json](resultados_eda/resumen_inec.json) |
| Resumen EDA MSP | [resumen_msp.json](resultados_eda/resumen_msp.json) |
| Validación conjunta | [resumen_validacion.json](resultados_validacion/resumen_validacion.json) |
| Cobertura provincia-mes | [cobertura_provincia_mes.csv](resultados_validacion/cobertura_provincia_mes.csv) |
| Diagnósticos compartidos | [cie3_compartidos_corregidos.csv](resultados_validacion/cie3_compartidos_corregidos.csv) |

### Diagramas, Turtle y scripts

| Recurso | Enlace directo |
|---|---|
| MER — imagen | [Modelo entidad-relación (PNG)](modelos/Modelo%20Entidad-Relaci%C3%B3n%20%28MER%29.png) |
| MER — editable | [Modelo entidad-relación (draw.io)](modelos/Modelo%20Entidad-Relaci%C3%B3n%20%28MER%29.drawio) |
| Esquema RDF — imagen | [Esquema semántico (PNG)](modelos/Esquema%20Semantico%20RDF%20-%20Salud%20Publica.png) |
| Esquema RDF — editable | [Esquema semántico (draw.io)](modelos/Esquema%20Semantico%20RDF%20-%20Salud%20Publica.drawio) |
| Esquema RDF — TBox | [esquema_semantico.ttl](rdf/esquema_semantico.ttl) |
| Instancias RDF — ABox | [instancias_salud_publica_2024.ttl](rdf/instancias_salud_publica_2024.ttl) |
| Exploración EDA | [eda_fuentes_salud_2024.py](scripts/eda_fuentes_salud_2024.py) |
| Validación de fuentes | [validacion_cie_territorio_2024.py](scripts/validacion_cie_territorio_2024.py) |
| Muestreo estratificado | [muestreo_salud_2024.py](scripts/muestreo_salud_2024.py) |
| Transformación a RDF | [construccion_grafo_salud_2024.R](scripts/construccion_grafo_salud_2024.R) |

### Consultas SPARQL

Las consultas se ejecutaron en **GraphDB**, sobre el repositorio `salud-publica-ecuador-2024`, después de importar ambos archivos Turtle. Las dos primeras consultas utilizan `FROM onto:explicit` para contar únicamente tripletas explícitas.

| Consulta | Archivo |
|---|---|
| Número de tripletas explícitas | [01_total_tripletas.sparql](consultas/01_total_tripletas.sparql) |
| Instancias por clase RDF | [02_verificacion_clases.sparql](consultas/02_verificacion_clases.sparql) |
| Atenciones y relaciones diagnósticas/temporales | [03_exploracion_emergencias.sparql](consultas/03_exploracion_emergencias.sparql) |
| Integración entre INEC y MSP mediante `A049` | [04_integracion_inec_msp.sparql](consultas/04_integracion_inec_msp.sparql) |

### Evidencias de GraphDB

| Punto del informe | Captura | Archivo |
|---|---|---|
| 14 — Implementación | Repositorio creado y activo | [01_repositorio_graphdb.png](evidencias/01_repositorio_graphdb.png) |
| 14 — Implementación | Importación de los archivos Turtle | [02_importacion_turtle.png](evidencias/02_importacion_turtle.png) |
| 14 — Implementación | Verificación de 138.476 tripletas | [03_total_tripletas.png](evidencias/03_total_tripletas.png) |
| 14 — Implementación | Verificación de las siete clases | [04_verificacion_clases.png](evidencias/04_verificacion_clases.png) |
| 15 — Exploración | Consulta de atenciones del MSP | [05_consulta_atenciones.png](evidencias/05_consulta_atenciones.png) |
| 15 — Exploración | Grafo de una atención del MSP | [06_grafo_atencion_msp.png](evidencias/06_grafo_atencion_msp.png) |
| 15 — Exploración | Consulta de integración por `A049` | [07_consulta_integracion_a049.png](evidencias/07_consulta_integracion_a049.png) |
| 15 — Exploración | Grafo de un egreso del INEC | [08_grafo_egreso_inec.png](evidencias/08_grafo_egreso_inec.png) |
| 15 — Exploración | Integración visual INEC–MSP por `A049` | [09_grafo_integracion_a049.png](evidencias/09_grafo_integracion_a049.png) |
| 15 — Exploración | Exploración ampliada de relaciones | [10_grafo_integracion_ampliado.png](evidencias/10_grafo_integracion_ampliado.png) |

## Cómo reproducir el proyecto

**Requisitos:** Python 3, paquete `pandas` para EDA/validación; R y paquete `rdflib`; GraphDB. Los archivos de origen se obtienen desde los portales oficiales enlazados anteriormente.

1. Colocar los dos CSV originales en la **raíz del repositorio**, conservando sus nombres. Estos archivos permanecen localmente y no deben añadirse al repositorio público sin verificar las condiciones de redistribución.
2. Desde la raíz, ejecutar la exploración y validación:

   ```powershell
   python -m pip install pandas
   python scripts/eda_fuentes_salud_2024.py
   python scripts/validacion_cie_territorio_2024.py
   ```

3. Generar las muestras, utilizando `resultados_validacion/cobertura_provincia_mes.csv`:

   ```powershell
   python scripts/muestreo_salud_2024.py
   ```

4. En R, establecer la raíz del proyecto como directorio de trabajo, instalar `rdflib` una sola vez y ejecutar el script de transformación:

   ```r
   install.packages("rdflib")  # Solo si no esta instalado
   source("scripts/construccion_grafo_salud_2024.R", encoding = "UTF-8")
   ```

   El archivo generado se guarda en `resultados_1C/instancias_salud_publica_2024.ttl`. La copia versionada para la entrega se encuentra en `rdf/`.

5. En GraphDB, crear o seleccionar el repositorio `salud-publica-ecuador-2024`, importar **ambos** archivos de `rdf/` desde **Import → User data** y ejecutar las consultas de `consultas/`.

> **Importante para reproducir:** los tres scripts Python deben resolver la raíz del proyecto con `CARPETA = Path(__file__).resolve().parent.parent`, porque se almacenan en `scripts/`. El script R debe ejecutarse desde la raíz y no incluir un `setwd()` con la ruta privada de un equipo. Estos ajustes son necesarios antes de publicar los scripts definitivos.

## Consideraciones y límites

- La integración se realiza a través de recursos compartidos, **no** mediante identificación de pacientes.
- Se conservaron los episodios con atributos idénticos, ya que la igualdad de columnas no prueba duplicación clínica.
- Los datos ausentes no se sustituyeron por información inventada; tampoco se completaron códigos territoriales oficiales sin verificar sus equivalencias.
- El uso de una muestra con cuota mínima por provincia-mes permite cubrir todas las zonas y meses, pero **no reproduce directamente los volúmenes nacionales**.
- Las evidencias y las consultas corresponden al prototipo académico implementado en GraphDB; no constituyen un sistema operativo de gestión sanitaria.

## Créditos y atribución

**Grupo 2 — Práctica bimestral 1:** María Valentina Samaniego Vásquez, María Esther Méndez Armijos y Manuel Alberto Gómez Vásquez.  
**Asignatura:** Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos.

Los conjuntos de datos proceden del **INEC** y del **MSP del Ecuador**. Los vocabularios empleados incluyen RDF/RDFS, XSD, Schema.org, Dublin Core, DCAT y SKOS. El repositorio reúne recursos técnicos y evidencias de una actividad académica.
