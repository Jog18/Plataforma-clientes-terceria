"""Limpieza de los registros de inspección y reglas de negocio de HBPO.

Recibe las filas "crudas" que entrega la fuente (todo en texto, tal como
viene de la hoja) y regresa filas limpias y con tipos correctos, listas para
que el navegador calcule KPIs y gráficas.

Reglas acordadas con Jesús (2026-09-30):
    scrap      = PIEZAS NOK
    retrabajo  = PIEZAS INSP.   (todo lo inspeccionado es pieza retrabajada)
    ok         = PIEZAS INSP. - PIEZAS NOK
"""

import re
from datetime import date, datetime, timedelta

from app.servicios.partes import estandarizar_parte

# Nombres de columna en la hoja. Si algún día cambian en la hoja, solo se
# cambian aquí.
COL_ID = "ID"
COL_FECHA = "FECHA"
COL_TURNO = "TURNO"
COL_HORA = "HORA"
COL_PARTE = "NUMERO DE PARTE"
COL_SERIAL = "SERIAL"
COL_FECHA_PROD = "FECHA DE PRODUCCION"
COL_INSP = "PIEZAS INSP."
COL_NOK = "PIEZAS NOK"
COL_COMENTARIOS = "COMENTARIOS"

# Pestaña "Detalle Defectos".
COL_DEF_ID_INSP = "ID INSPECCION"
COL_DEF_DEFECTO = "DEFECTO"
COL_DEF_CANTIDAD = "CANTIDAD"
COL_DEF_TEXTO = "TEXTO"

# El día de producción cierra a las 6:00 (Jesús, 2026-10-07). Turnos:
# 1ro 6:00-14:00, 2do 14:00-21:00, 3ro 21:30-6:00. Todo lo capturado antes
# de las 6:00 cuenta para el día anterior, así el 3er turno completo queda en
# el día en que empezó.
HORA_CIERRE_DIA = 6

# Formatos de fecha que acepta la limpieza, en orden de prueba.
FORMATOS_FECHA = ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d")


# ---- conversiones básicas --------------------------------------------------

def a_entero(texto: str) -> int:
    """'12' -> 12, '' -> 0, '1,250' -> 1250, '3.0' -> 3. Basura -> 0."""
    texto = (texto or "").strip().replace(",", "")
    if not texto:
        return 0
    try:
        return int(float(texto))
    except ValueError:
        return 0


def a_fecha(texto: str) -> date | None:
    """'2/9/2026' -> date(2026, 9, 2). Si no se entiende, None."""
    texto = (texto or "").strip()
    if not texto:
        return None
    # A veces viene con hora ("2/9/2026 14:05"); nos quedamos con la fecha.
    texto = texto.split(" ")[0]
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def limpiar_texto(texto: str) -> str:
    """Quita espacios sobrantes: '  P8MB863242K  BDE ' -> 'P8MB863242K BDE'."""
    return re.sub(r"\s+", " ", (texto or "")).strip()


# La app de captura escribe "LAZER"; la palabra correcta es "LÁSER"
# (Jesús, 2026-10-08). También se unifica "LASER" sin acento para que el
# tablero no cuente el mismo defecto dos veces.
PATRON_LASER = re.compile(r"\bl[aá][sz]er\b", re.IGNORECASE)


def corregir_laser(texto: str) -> str:
    """'LAZER NOK' -> 'LÁSER NOK', 'lazer chueco' -> 'láser chueco'."""
    def reemplazo(m: re.Match) -> str:
        palabra = m.group(0)
        if palabra.isupper():
            return "LÁSER"
        if palabra[0].isupper():
            return "Láser"
        return "láser"
    return PATRON_LASER.sub(reemplazo, texto or "")


def leer_id(texto: str) -> str:
    """El ID lo genera la app como texto hexadecimal ('e21c0dc4', '26456617').

    Se trata siempre como texto: convertirlo a número pierde los que traen
    letras. Se pasa a minúsculas para que el cruce con defectos no falle.
    """
    return (texto or "").strip().lower()


def normalizar_hora(texto: str) -> str:
    """'8:21:42' -> '08:21:42', '13:03' -> '13:03:00'.

    La hoja guarda la hora sin cero a la izquierda. Como texto, '8:21:42'
    queda después de '13:03:42' al ordenar o comparar, así que se entrega
    siempre con dos dígitos por parte. Si no se entiende, se regresa tal cual.
    """
    texto = limpiar_texto(texto)
    partes = texto.split(":")
    if not texto or not 2 <= len(partes) <= 3 or not all(p.strip().isdigit() for p in partes):
        return texto
    h, m, seg = ([int(p) for p in partes] + [0])[:3]
    return f"{h:02d}:{m:02d}:{seg:02d}"


def _hora_ordenable(hora: str) -> tuple[int, int, int]:
    """'8:26:31' -> (8, 26, 31) para ordenar bien ('10:00' va después de '9:00')."""
    partes = [a_entero(p) for p in (hora or "").split(":")]
    return tuple((partes + [0, 0, 0])[:3])


def dia_produccion(fecha: date, hora: str) -> date:
    """Día al que pertenece un registro: de 6:00 a 5:59 del día siguiente.

    date(2026, 10, 6) + '02:30:00' -> date(2026, 10, 5)  (3er turno del lunes 5)
    date(2026, 10, 6) + '06:00:00' -> date(2026, 10, 6)
    Si la hora no se entiende, se queda la fecha de captura.
    """
    partes = (hora or "").split(":")
    if not partes[0].strip().isdigit():
        return fecha
    if int(partes[0]) < HORA_CIERRE_DIA:
        return fecha - timedelta(days=1)
    return fecha


# ---- limpieza de registros -------------------------------------------------

def agrupar_defectos(filas_defectos: list[dict]) -> dict[str, list[dict]]:
    """Pasa 'Detalle Defectos' a un diccionario: id de inspección -> sus defectos."""
    por_inspeccion: dict[str, list[dict]] = {}
    for fila in filas_defectos:
        id_insp = leer_id(fila.get(COL_DEF_ID_INSP, ""))
        if not id_insp:
            continue
        por_inspeccion.setdefault(id_insp, []).append({
            "defecto": corregir_laser(limpiar_texto(fila.get(COL_DEF_DEFECTO, "")).upper()),
            "cantidad": a_entero(fila.get(COL_DEF_CANTIDAD, "")),
            "texto": corregir_laser(limpiar_texto(fila.get(COL_DEF_TEXTO, ""))),
        })
    return por_inspeccion


def limpiar_registro(fila: dict, defectos: list[dict]) -> dict | None:
    """Convierte una fila cruda de 'Inspeccion HBPO' en un registro limpio.

    Regresa None si la fila no sirve (sin ID o sin fecha válida).
    """
    id_insp = leer_id(fila.get(COL_ID, ""))
    fecha = a_fecha(fila.get(COL_FECHA, ""))
    if not id_insp or fecha is None:
        return None

    insp = a_entero(fila.get(COL_INSP, ""))
    nok = a_entero(fila.get(COL_NOK, ""))
    fecha_prod = a_fecha(fila.get(COL_FECHA_PROD, ""))
    hora = normalizar_hora(fila.get(COL_HORA, ""))

    return {
        "id": id_insp,
        "fecha": fecha.isoformat(),          # fecha de captura, 'YYYY-MM-DD'
        # Día con el que se agrupa y filtra en el tablero (cierra a las 6:00).
        "dia_produccion": dia_produccion(fecha, hora).isoformat(),
        "turno": limpiar_texto(fila.get(COL_TURNO, "")),
        "hora": hora,
        "parte": estandarizar_parte(fila.get(COL_PARTE, "")),
        "serial": limpiar_texto(fila.get(COL_SERIAL, "")),
        "fecha_produccion": fecha_prod.isoformat() if fecha_prod else None,
        "insp": insp,
        "nok": nok,
        # Reglas de negocio HBPO:
        "scrap": nok,
        "retrabajo": insp,
        "ok": max(insp - nok, 0),
        "comentarios": corregir_laser(limpiar_texto(fila.get(COL_COMENTARIOS, ""))),
        "defectos": defectos,
    }


def construir_paquete(filas_inspeccion: list[dict], filas_defectos: list[dict]) -> dict:
    """Arma el JSON completo que recibirá el navegador.

    Además de las filas limpias incluye los catálogos (defectos, turnos,
    partes) para llenar los filtros sin recorrer todo de nuevo en JavaScript.
    """
    defectos_por_insp = agrupar_defectos(filas_defectos)

    registros = []
    descartados = 0
    for fila in filas_inspeccion:
        limpio = limpiar_registro(fila, defectos_por_insp.get(leer_id(fila.get(COL_ID, "")), []))
        if limpio is not None:
            registros.append(limpio)
        else:
            # Fila con algún dato pero sin ID o sin fecha válida.
            descartados += 1
    # Mismo orden que la hoja: por fecha y, dentro del día, por hora.
    registros.sort(key=lambda r: (r["fecha"], _hora_ordenable(r["hora"])))

    catalogo_defectos = sorted({d["defecto"] for r in registros for d in r["defectos"] if d["defecto"]})
    turnos = sorted({r["turno"] for r in registros if r["turno"]})
    partes = sorted({r["parte"] for r in registros if r["parte"]})

    return {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "cliente": "HBPO",
        "total_registros": len(registros),
        "descartados": descartados,
        "defectos": catalogo_defectos,
        "turnos": turnos,
        "partes": partes,
        "filas": registros,
    }
