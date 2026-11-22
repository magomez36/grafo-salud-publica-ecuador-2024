# ==============================================================================
# PRACTICA BIMESTRAL 1C - Transformacion de CSV a RDF - Salud publica 2024
# ==============================================================================

library(rdflib)

setwd("C:/Users/manuelgomez/Desktop/Interoperabilidad y Explotación de Datos en Ecosistemas Heterogéneos/Semana 8 - Datos/Práctica Bimestral")


# ==============================================================================
# Ingesta de datos crudos (muestras elaboradas previamente en Python)
# ==============================================================================

leer_csv <- function(archivo) {
  read.csv2(archivo, fileEncoding = "UTF-8-BOM", stringsAsFactors = FALSE,
            colClasses = "character", check.names = FALSE, na.strings = character(0))
}

carpeta_datos <- if (file.exists("datos_muestreados/muestra_inec_2024.csv")) {
  "datos_muestreados"
} else {
  "datos"
}

file.exists("datos_muestreados/muestra_inec_2024.csv")
file.exists("datos_muestreados/muestra_msp_2024.csv")

inec <- leer_csv(file.path(carpeta_datos, "muestra_inec_2024.csv"))
msp  <- leer_csv(file.path(carpeta_datos, "muestra_msp_2024.csv"))

dir.create("resultados_1C", showWarnings = FALSE)


# ==============================================================================
# Comprobacion basica de las muestras y su trazabilidad
# ==============================================================================

requeridos_inec <- c("numero_fila_origen", "prov_ubi", "cant_ubi", "parr_ubi",
                     "prov_res", "cant_res", "parr_res", "fecha_ingr", "fecha_egr",
                     "cau_cie10", "causa3", "sexo", "edad", "dia_estad")

requeridos_msp <- c("numero_fila_origen", "PROVINCIA", "CANTON", "PARROQUIA",
                    "PROVINCIA_DOM", "FECHA_DE_ATENCION", "UNICODIGO",
                    "ESTABLECIMIENTO", "CIE", "DIAGNOSTICO")

if (!all(requeridos_inec %in% names(inec)) ||
    !all(requeridos_msp %in% names(msp))) stop("Faltan columnas obligatorias.")

if (nrow(inec) != 2592L || nrow(msp) != 2592L) stop("Tamano de muestra inesperado.")

if (anyDuplicated(inec$numero_fila_origen) || anyDuplicated(msp$numero_fila_origen)) {
  stop("Hay identificadores de fila de origen duplicados.")
}


# ==============================================================================
# Identificadores y vocabularios (mismos nombres que esquema_semantico.ttl)
# ==============================================================================

BASE <- "https://example.org/salud-ecuador/"
RDF  <- "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS <- "http://www.w3.org/2000/01/rdf-schema#"
XSD  <- "http://www.w3.org/2001/XMLSchema#"
SKOS <- "http://www.w3.org/2004/02/skos/core#"

uri_egreso <- function(id) paste0(BASE, "egreso/INEC_", id)
uri_atencion <- function(id) paste0(BASE, "atencion/MSP_", id)
uri_establecimiento <- function(id) paste0(BASE, "establecimiento/MSP_", id)
uri_periodo <- function(mes) paste0(BASE, "periodo/2024_", sprintf("%02d", mes))
uri_cie3 <- function(c) paste0(BASE, "diagnostico/CIE3_", c)
uri_cie <- function(c) paste0(BASE, "diagnostico/CIE_", c)


# ==============================================================================
# Normalizacion minima y tratamiento de valores faltantes
# ==============================================================================

normalizar <- function(x) {
  y <- toupper(trimws(as.character(x)))
  z <- suppressWarnings(iconv(y, from = "UTF-8", to = "ASCII//TRANSLIT"))
  z[is.na(z)] <- y[is.na(z)]
  trimws(gsub("[[:space:]]+", " ", gsub("[^A-Z0-9 ]", " ", z)))
}

limpiar <- function(x) {
  if (length(x) != 1L || is.na(x)) return(NA_character_)
  x <- trimws(as.character(x))
  if (normalizar(x) %in% c("", "NA", "N A", "NULL", "NAN", "SIN INFORMACION",
                           "NO INFORMADO", "NO REGISTRA", "S I", "S D")) {
    return(NA_character_)
  }
  x
}

slug <- function(x) gsub(" ", "_", normalizar(x), fixed = TRUE)

codigo_cie <- function(x) {
  x <- toupper(trimws(as.character(x)))
  patron <- "^[A-Z][0-9]{2}[A-Z0-9]{0,4}(?=[[:space:]]|$|[.,;])"
  p <- regexpr(patron, x, perl = TRUE)
  if (is.na(x) || p[1] == -1L) return(NA_character_)
  regmatches(x, p)
}

descripcion_inec <- function(x) {
  x <- limpiar(x)
  if (is.na(x)) return(NA_character_)
  y <- trimws(sub("^[A-Za-z][0-9]{2}[A-Za-z0-9]{0,4}[[:space:]]*", "", x))
  if (identical(x, y) || !nzchar(y)) NA_character_ else y
}


# ==============================================================================
# Motor de tripletas RDF (mismo mecanismo utilizado por el profesor)
# ==============================================================================

g <- rdf()

creados <- new.env(hash = TRUE, parent = emptyenv())

contador_territorios <- 0L

add_uri <- function(s, p, o) {
  if (is.na(s) || is.na(o)) return(invisible(NULL))
  rdf_add(g, subject = s, predicate = p, object = o,
          subjectType = "uri", objectType = "uri")
}

add_lit <- function(s, p, valor, tipo = "string") {
  valor <- limpiar(valor)
  if (is.na(valor)) return(invisible(NULL))
  if (tipo == "integer" && !grepl("^[0-9]+$", valor)) return(invisible(NULL))
  if (tipo == "date" && is.na(as.Date(valor, format = "%Y-%m-%d"))) {
    return(invisible(NULL))
  }
  rdf_add(g, subject = s, predicate = p, object = valor,
          subjectType = "uri", objectType = "literal",
          datatype_uri = paste0(XSD, tipo))
}

propiedad <- function(s, p, v, tipo = "string") add_lit(s, paste0(BASE, p), v, tipo)

relacion <- function(s, p, o) add_uri(s, paste0(BASE, p), o)

instancia <- function(uri, clase, etiqueta = NA_character_) {
  if (exists(uri, envir = creados, inherits = FALSE)) return(FALSE)
  assign(uri, TRUE, envir = creados)
  add_uri(uri, paste0(RDF, "type"), paste0(BASE, clase))
  add_lit(uri, paste0(RDFS, "label"), etiqueta)
  TRUE
}


# ==============================================================================
# Dimensiones: Territorio (jerarquia provincia > canton > parroquia)
# ==============================================================================

provincias <- unique(c(normalizar(inec$prov_ubi), normalizar(msp$PROVINCIA)))
if (length(provincias) != 24L) stop("La muestra debe cubrir 24 provincias.")

crear_territorio <- function(provincia, canton = NA_character_, parroquia = NA_character_) {
  p <- normalizar(provincia)
  if (!(p %in% provincias)) return(NA_character_)
  up <- paste0(BASE, "territorio/PROV_", slug(p))
  if (instancia(up, "Territorio", p)) {
    contador_territorios <<- contador_territorios + 1L
    propiedad(up, "idTerritorio", contador_territorios, "integer")
    propiedad(up, "nombre", p)
    propiedad(up, "nivelTerritorial", "Provincia")
  }
  actual <- up
  if (!is.na(limpiar(canton))) {
    c <- normalizar(canton)
    if (p == "PICHINCHA" && c == "DISTRITO METROPOLITANO DE QUITO") c <- "QUITO"
    uc <- paste0(BASE, "territorio/CANT_", slug(p), "_", slug(c))
    if (instancia(uc, "Territorio", c)) {
      contador_territorios <<- contador_territorios + 1L
      propiedad(uc, "idTerritorio", contador_territorios, "integer")
      propiedad(uc, "nombre", c)
      propiedad(uc, "nivelTerritorial", "Canton")
    }
    relacion(up, "contieneTerritorio", uc)
    actual <- uc
    if (!is.na(limpiar(parroquia))) {
      q <- normalizar(parroquia)
      uq <- paste0(BASE, "territorio/PARR_", slug(p), "_", slug(c), "_", slug(q))
      if (instancia(uq, "Territorio", q)) {
        contador_territorios <<- contador_territorios + 1L
        propiedad(uq, "idTerritorio", contador_territorios, "integer")
        propiedad(uq, "nombre", q)
        propiedad(uq, "nivelTerritorial", "Parroquia")
      }
      relacion(uc, "contieneTerritorio", uq)
      actual <- uq
    }
  }
  actual
}


# ==============================================================================
# Dimensiones: Diagnostico CIE-10 (codigo completo y categoria CIE-3)
# ==============================================================================

crear_diagnostico <- function(valor, descripcion = NA_character_, descripcion3 = NA_character_) {
  codigo <- codigo_cie(valor)
  if (is.na(codigo)) return(NA_character_)
  tres <- substr(codigo, 1L, 3L)
  cat <- uri_cie3(tres)
  if (instancia(cat, "DiagnosticoCIE10", tres)) {
    propiedad(cat, "codigoCIE10", tres)
    propiedad(cat, "codigoCIE10_3", tres)
    propiedad(cat, "descripcion", descripcion3)
  }
  if (nchar(codigo) == 3L) return(cat)
  det <- uri_cie(codigo)
  if (instancia(det, "DiagnosticoCIE10", codigo)) {
    propiedad(det, "codigoCIE10", codigo)
    propiedad(det, "codigoCIE10_3", tres)
    propiedad(det, "descripcion", descripcion)
  }
  add_uri(det, paste0(SKOS, "broader"), cat)
  det
}


# ==============================================================================
# Dimensiones: Periodos mensuales
# ==============================================================================

meses <- c("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
           "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")

for (mes in seq_len(12)) {
  u <- uri_periodo(mes)
  inicio <- as.Date(sprintf("2024-%02d-01", mes))
  fin <- seq(inicio, by = "month", length.out = 2L)[2] - 1
  instancia(u, "Periodo", paste(meses[mes], "2024"))
  propiedad(u, "idPeriodo", 202400 + mes, "integer")
  propiedad(u, "anio", 2024, "integer")
  propiedad(u, "mesNumero", mes, "integer")
  propiedad(u, "nombreMes", meses[mes])
  propiedad(u, "fechaInicio", as.character(inicio), "date")
  propiedad(u, "fechaFin", as.character(fin), "date")
}

periodo_fecha <- function(x) {
  f <- as.Date(limpiar(x), format = "%Y-%m-%d")
  if (is.na(f) || format(f, "%Y") != "2024") return(NA_character_)
  uri_periodo(as.integer(format(f, "%m")))
}


# ==============================================================================
# Dimensiones: Fuentes institucionales
# ==============================================================================

fuente_inec <- paste0(BASE, "fuente/INEC_2024")
fuente_msp <- paste0(BASE, "fuente/MSP_2024")

instancia(fuente_inec, "FuenteDatos", "INEC - Egresos hospitalarios 2024")
propiedad(fuente_inec, "idFuente", 1, "integer")
propiedad(fuente_inec, "nombreArchivo", "egresos_hospitalarios_2024.csv")
propiedad(fuente_inec, "institucionResponsable", "Instituto Nacional de Estadistica y Censos")
propiedad(fuente_inec, "identificadorFuente", "INEC_PDA_2025")
propiedad(fuente_inec, "documentoReferencia", "INEC_DIES_EEH_2024")
propiedad(fuente_inec, "anioDatos", 2024, "integer")
propiedad(fuente_inec, "formato", "CSV")

instancia(fuente_msp, "FuenteDatos", "MSP - Emergencias 2024")
propiedad(fuente_msp, "idFuente", 2, "integer")
propiedad(fuente_msp, "nombreArchivo", "MSP_Emergencias_2024.csv")
propiedad(fuente_msp, "institucionResponsable", "Ministerio de Salud Publica")
propiedad(fuente_msp, "identificadorFuente", "MSP-04-2024-V1")
propiedad(fuente_msp, "documentoReferencia", "MSP_Directorio_2024Diciembre")
propiedad(fuente_msp, "anioDatos", 2024, "integer")
propiedad(fuente_msp, "formato", "CSV")


# ==============================================================================
# Transformacion de cada egreso INEC a instancias y tripletas
# ==============================================================================

for (i in seq_len(nrow(inec))) {
  f <- inec[i, , drop = FALSE]
  u <- uri_egreso(f$numero_fila_origen)
  instancia(u, "EgresoHospitalario", paste("Egreso INEC", f$numero_fila_origen))
  relacion(fuente_inec, "contieneEgresoHospitalario", u)
  relacion(u, "tienePeriodoEgreso", periodo_fecha(f$fecha_egr))
  relacion(u, "ocurreEnTerritorio", crear_territorio(f$prov_ubi, f$cant_ubi, f$parr_ubi))
  relacion(u, "registraResidenciaEgreso", crear_territorio(f$prov_res, f$cant_res, f$parr_res))
  dx <- crear_diagnostico(f$cau_cie10, descripcion_inec(f$cau_cie10),
                          descripcion_inec(f$causa3))
  relacion(u, "tieneDiagnosticoEgreso", dx)
  propiedad(u, "idEgreso", f$numero_fila_origen, "integer")
  propiedad(u, "fechaIngreso", f$fecha_ingr, "date")
  propiedad(u, "fechaEgreso", f$fecha_egr, "date")
  propiedad(u, "diasEstada", f$dia_estad, "integer")
  propiedad(u, "sexoEgreso", normalizar(f$sexo))
  propiedad(u, "edadEgreso", f$edad, "integer")
  propiedad(u, "condicionEdadEgreso", f$cod_edad)
  propiedad(u, "nacionalidadEgreso", f$nac_pac)
  propiedad(u, "codigoPais", f$cod_pais)
  propiedad(u, "nombrePais", f$nom_pais)
  propiedad(u, "etnia", f$etnia)
  propiedad(u, "tipoSeguro", f$tipo_seg)
  propiedad(u, "discapacidad", f$dis_pac)
  propiedad(u, "condicionEgreso", f$con_egrpa)
  propiedad(u, "especialidadEgreso", f$esp_egrpa)
  propiedad(u, "areaUbicacion", f$area_ubi)
  propiedad(u, "areaResidencia", f$area_res)
  propiedad(u, "mesInvestigacion", f$mes_inv)
  propiedad(u, "claseEstablecimiento", f$clase)
  propiedad(u, "tipoEstablecimiento", f$tipo)
  propiedad(u, "entidad", f$entidad)
  propiedad(u, "sector", f$sector)
  propiedad(u, "causa3", f$causa3)
  propiedad(u, "capituloCIE10INEC", f$cap221rx)
  propiedad(u, "causaLista221", f$cau221rx)
  propiedad(u, "causaLista298", f$cau298rx)
}


# ==============================================================================
# Transformacion de cada atencion MSP a instancias y tripletas
# ==============================================================================

for (i in seq_len(nrow(msp))) {
  f <- msp[i, , drop = FALSE]
  u <- uri_atencion(f$numero_fila_origen)
  instancia(u, "AtencionEmergencia", paste("Atencion MSP", f$numero_fila_origen))
  relacion(fuente_msp, "contieneAtencionEmergencia", u)
  relacion(u, "tienePeriodoEmergencia", periodo_fecha(f$FECHA_DE_ATENCION))
  lugar <- crear_territorio(f$PROVINCIA, f$CANTON, f$PARROQUIA)
  relacion(u, "registraResidenciaEmergencia", crear_territorio(f$PROVINCIA_DOM))
  relacion(u, "tieneDiagnosticoEmergencia", crear_diagnostico(f$CIE, f$DIAGNOSTICO))
  propiedad(u, "idAtencion", f$numero_fila_origen, "integer")
  propiedad(u, "fechaAtencion", f$FECHA_DE_ATENCION, "date")
  propiedad(u, "sexoAtencion", normalizar(f$SEXO))
  propiedad(u, "edadAtencion", f$EDAD, "integer")
  propiedad(u, "condicionEdadAtencion", f[["CONDICIÓN_EDAD"]])
  propiedad(u, "nacionalidadAtencion", f$NACIONALIDAD)
  propiedad(u, "condicionDiagnostico", f[["CONDICIÓN_DIAGNÓSTICO"]])
  codigo_est <- limpiar(f$UNICODIGO)
  if (!is.na(codigo_est)) {
    establecimiento <- uri_establecimiento(codigo_est)
    if (instancia(establecimiento, "EstablecimientoSalud", f$ESTABLECIMIENTO)) {
      propiedad(establecimiento, "unicodigo", codigo_est)
      propiedad(establecimiento, "nombreEstablecimiento", f$ESTABLECIMIENTO)
      propiedad(establecimiento, "zona", f$ZONA)
      propiedad(establecimiento, "distrito", f$DISTRITO)
    }
    relacion(lugar, "ubicaEstablecimiento", establecimiento)
    relacion(establecimiento, "registraAtencion", u)
  }
}


# ==============================================================================
# Serializacion Turtle y comprobacion de integridad
# ==============================================================================

archivo <- "resultados_1C/instancias_salud_publica_2024.ttl"

ns <- c(ex = BASE, rdf = RDF, rdfs = RDFS, xsd = XSD, skos = SKOS)

rdf_serialize(g, archivo, format = "turtle", namespace = ns)

total_tripletas <- length(g)

g_verificado <- rdf_parse(archivo, format = "turtle")

if (length(g_verificado) != total_tripletas) stop("La verificacion Turtle no coincide.")


# ==============================================================================
# Resumen de resultados para el informe acumulativo
# ==============================================================================

resumen <- c(
  "Practica bimestral 1C - Transformacion RDF Salud Publica Ecuador 2024",
  paste("Muestras: INEC", nrow(inec), "| MSP", nrow(msp)),
  paste("Registros sanitarios:", nrow(inec) + nrow(msp)),
  paste("Recursos instanciados:", length(ls(creados))),
  paste("Tripletas de instancias (ABox):", total_tripletas),
  paste("Archivo Turtle:", archivo),
  "Esquema (TBox): rdf/esquema_semantico.ttl se importa por separado.",
  "Muestreo y normalizacion documentados en los scripts de Python.",
  "No se eliminaron episodios por tener atributos iguales.",
  "Los codigos territoriales oficiales no se inventaron ni completaron.",
  "Diagnosticos detallados relacionados con su categoria CIE-3 por skos:broader."
)

writeLines(resumen, "resultados_1C/resumen_transformacion.txt", useBytes = TRUE)

cat("INEC:", nrow(inec), "| MSP:", nrow(msp), "\n")
cat("Recursos:", length(ls(creados)), "| Tripletas ABox:", total_tripletas, "\n")
cat("Turtle validado:", archivo, "\n")

# ==============================================================================


