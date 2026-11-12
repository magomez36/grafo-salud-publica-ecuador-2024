# Grafo de conocimiento sobre salud pública en Ecuador (2024)

**Práctica bimestral 1 — Grupo 2**  

Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos  

## Descripción

Proyecto académico para diseñar y, en la etapa final, implementar un **grafo de conocimiento RDF** sobre salud pública en Ecuador. Integra conceptualmente dos fuentes oficiales correspondientes a **2024**:

- **INEC:** egresos hospitalarios.
- **MSP:** atenciones de emergencia.

La integración se plantea a través de **territorio, diagnóstico CIE-10 y período**. No se pretende vincular pacientes ni episodios individuales entre ambas fuentes, porque no se ha identificado un identificador común que permita hacerlo de forma fiable.

## Objetivo y etapas

Modelar datos heterogéneos como datos enlazados, mediante un modelo entidad-relación, un esquema semántico RDF y, posteriormente, su transformación, carga y consulta en GraphDB.

| Entrega | Alcance | Estado |
|---|---|---|
| **1A** | Definición del dominio, problema, preguntas de competencia y fuentes | Desarrollada |
| **1B** | Obtención/caracterización de datos, MER, esquema RDF y vocabularios abiertos | Desarrollada |
| **1C** | Transformación a tripletas RDF, implementación en GraphDB y consultas SPARQL | Pendiente |


## Fuentes de datos y descarga

| Fuente | Organismo | Archivo original previsto | Registros | Variables |
|---|---|---|---|---|
| Egresos hospitalarios 2024 | INEC | `egresos_hospitalarios_2024.csv` | 1.132.667, según la publicación institucional | 38 |
| Atenciones de emergencia 2024 | MSP | `MSP_Emergencias_2024.csv` | Pendiente de verificar mediante recuento del archivo completo | 16, según caracterización preliminar |

**Fuentes oficiales:**

- [INEC — Camas y egresos hospitalarios](https://www.ecuadorencifras.gob.ec/camas-y-egresos-hospitalarios/)
- [INEC — Catálogo de metadatos de egresos 2024](https://anda.inec.gob.ec/anda5/index.php/catalog/1151)
- [MSP — Directorio de archivos de 2024](https://almacenamiento.msp.gob.ec/index.php/s/yDCA3vZfSgZZpJk?path=%2F2024)


## Estructura del repositorio

```text
grafo-salud-publica-ecuador-2024/
├── README.md
├── datos/
│   ├── README.md
│   └── muestras/
│       ├── muestra_inec.csv
│       └── muestra_msp.csv 
├── modelos/
│   ├── Modelo Entidad-Relación (MER).png
│   ├── Modelo Entidad-Relación (MER).drawio
│   ├── Esquema Semantico RDF - Salud Publica.png
│   └── Esquema Semantico RDF - Salud Publica.drawio
├── rdf/
│   └── esquema_semantico.ttl
├── scripts/             
└── consultas/
    └── README.md
```


## Uso y atribución

Los datos provienen de fuentes oficiales del INEC y el MSP. Su disponibilidad pública **no equivale necesariamente a permiso de redistribución**. Antes de adjuntar los archivos completos a una Release pública, deben verificarse sus licencias y que su publicación no exponga datos personales o sensibles. Si la redistribución no está autorizada, conservar enlaces a las fuentes oficiales y consultar al docente la forma válida de entregar los archivos.
