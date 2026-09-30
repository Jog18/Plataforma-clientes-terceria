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
from datetime import date, datetime

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


# ---- limpieza de registros -------------------------------------------------

def agrupar_defectos(filas_defectos: list[dict]) -> dict[int, list[dict]]:
    """Pasa 'Detalle Defectos' a un diccionario: id de inspección -> sus defectos."""
    por_inspeccion: dict[int, list[dict]] = {}
    for fila in filas_defectos:
        id_insp = a_entero(fila.get(COL_DEF_ID_INSP, ""))
        if id_insp == 0:
            continue
        por_inspeccion.setdefault(id_insp, []).append({
            "defecto": limpiar_texto(fila.get(COL_DEF_DEFECTO, "")).upper(),
            "cantidad": a_entero(fila.get(COL_DEF_CANTIDAD, "")),
            "texto": limpiar_texto(fila.get(COL_DEF_TEXTO, "")),
        })
    return por_inspeccion


def limpiar_registro(fila: dict, defectos: list[dict]) -> dict | None:
    """Convierte una fila cruda de 'Inspeccion HBPO' en un registro limpio.

    Regresa None si la fila no sirve (sin ID o sin fecha válida).
    """
    id_insp = a_entero(fila.get(COL_ID, ""))
    fecha = a_fecha(fila.get(COL_FECHA, ""))
    if id_insp == 0 or fecha is None:
        return None

    insp = a_entero(fila.get(COL_INSP, ""))
    nok = a_entero(fila.get(COL_NOK, ""))
    fecha_prod = a_fecha(fila.get(COL_FECHA_PROD, ""))

    return {
        "id": id_insp,
        "fecha": fecha.isoformat(),          # 'YYYY-MM-DD', fácil de ordenar y filtrar
        "turno": limpiar_texto(fila.get(COL_TURNO, "")),
        "hora": limpiar_texto(fila.get(COL_HORA, "")),
        "parte": limpiar_texto(fila.get(COL_PARTE, "")).upper(),
        "serial": limpiar_texto(fila.get(COL_SERIAL, "")),
        "fecha_produccion": fecha_prod.isoformat() if fecha_prod else None,
        "insp": insp,
        "nok": nok,
        # Reglas de negocio HBPO:
        "scrap": nok,
        "retrabajo": insp,
        "ok": max(insp - nok, 0),
        "comentarios": limpiar_texto(fila.get(COL_COMENTARIOS, "")),
        "defectos": defectos,
    }


def construir_paquete(filas_inspeccion: list[dict], filas_defectos: list[dict]) -> dict:
    """Arma el JSON completo que recibirá el navegador.

    Además de las filas limpias incluye los catálogos (defectos, turnos,
    partes) para llenar los filtros sin recorrer todo de nuevo en JavaScript.
    """
    defectos_por_insp = agrupar_defectos(filas_defectos)

    registros = []
    for fila in filas_inspeccion:
        limpio = limpiar_registro(fila, defectos_por_insp.get(a_entero(fila.get(COL_ID, "")), []))
        if limpio is not None:
            registros.append(limpio)
    registros.sort(key=lambda r: (r["fecha"], r["id"]))

    catalogo_defectos = sorted({d["defecto"] for r in registros for d in r["defectos"] if d["defecto"]})
    turnos = sorted({r["turno"] for r in registros if r["turno"]})
    partes = sorted({r["parte"] for r in registros if r["parte"]})

    return {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "cliente": "HBPO",
        "total_registros": len(registros),
        "defectos": catalogo_defectos,
        "turnos": turnos,
        "partes": partes,
        "filas": registros,
    }
