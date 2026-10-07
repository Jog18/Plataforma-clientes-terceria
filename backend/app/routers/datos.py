"""Rutas de datos del dashboard.

Un "router" es un grupo de rutas con un prefijo común (/api). main.py lo
registra en la app. Las rutas de login viven en routers/auth.py.

/api/datos y /api/excel exigen sesión: `obtener_cliente` depende de `usuario_actual`, que
responde 401 si no hay cookie válida. /api/salud sigue pública porque Render
la usa para vigilar el servicio.
"""

from datetime import date

import gspread
from fastapi import APIRouter, Depends, HTTPException, Response

from app.clientes import Cliente
from app.config import config
from app.dependencias import obtener_cliente, obtener_fuente
from app.fuentes.gsheets import FuenteGoogleSheets
from app.servicios import excel as reporte_excel
from app.servicios import inspeccion

router = APIRouter(prefix="/api", tags=["datos"])


@router.get("/salud")
def salud():
    """Responde si el servidor está vivo. Render lo usa para vigilarlo."""
    return {"estado": "ok"}


@router.get("/datos")
def datos(
    refrescar: bool = False,
    cliente: Cliente = Depends(obtener_cliente),
    fuente: FuenteGoogleSheets = Depends(obtener_fuente),
):
    """Paquete completo de registros limpios para el dashboard.

    Normalmente sale de la copia guardada (hasta `cache_segundos`). Con
    `?refrescar=1`, que usa el botón "Actualizar", se lee la hoja de nuevo,
    salvo que la copia tenga menos de `refresco_minimo_segundos`.
    """
    if refrescar:
        fuente.refrescar(config.refresco_minimo_segundos)
    paquete = _leer_paquete(cliente, fuente)
    paquete["cliente"] = cliente.nombre
    return paquete


@router.get("/excel")
def excel(
    desde: date,
    hasta: date,
    turno: str = "",
    parte: str = "",
    defecto: str = "",
    cliente: Cliente = Depends(obtener_cliente),
    fuente: FuenteGoogleSheets = Depends(obtener_fuente),
):
    """Reporte en Excel de un día o rango de días de producción (6:00 a 5:59).

    turno, parte y defecto son los filtros opcionales del tablero.
    """
    if hasta < desde:
        raise HTTPException(status_code=400, detail="La fecha final es anterior a la inicial.")
    paquete = _leer_paquete(cliente, fuente)
    filas = reporte_excel.filtrar(paquete["filas"], desde.isoformat(), hasta.isoformat(),
                                  turno, parte, defecto)
    contenido = reporte_excel.armar_libro(filas, paquete["defectos"], cliente.nombre)
    nombre = f"inspeccion_{cliente.nombre.lower()}_{desde}"
    if hasta != desde:
        nombre += f"_a_{hasta}"
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.xlsx"'},
    )


def _leer_paquete(cliente: Cliente, fuente: FuenteGoogleSheets) -> dict:
    """Lee las dos pestañas del cliente y regresa el paquete de filas limpias."""
    try:
        filas_insp = fuente.leer_tabla(cliente.pestana_inspeccion)
        filas_def = fuente.leer_tabla(cliente.pestana_defectos)
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error))
    except gspread.exceptions.WorksheetNotFound as error:
        raise HTTPException(status_code=500, detail=f"No existe la pestaña {error}")
    except gspread.exceptions.APIError as error:
        raise HTTPException(status_code=502, detail=f"Google respondió con error: {error}")
    return inspeccion.construir_paquete(filas_insp, filas_def)
