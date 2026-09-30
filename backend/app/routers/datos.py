"""Rutas de datos del dashboard.

Un "router" es un grupo de rutas con un prefijo común (/api). main.py lo
registra en la app. Cuando haya rutas de login o de administración, van en
su propio archivo dentro de routers/.
"""

import gspread
from fastapi import APIRouter, Depends, HTTPException

from app.clientes import Cliente
from app.dependencias import obtener_cliente, obtener_fuente
from app.fuentes.gsheets import FuenteGoogleSheets
from app.servicios import inspeccion

router = APIRouter(prefix="/api", tags=["datos"])


@router.get("/salud")
def salud():
    """Responde si el servidor está vivo. Render lo usa para vigilarlo."""
    return {"estado": "ok"}


@router.get("/datos")
def datos(
    cliente: Cliente = Depends(obtener_cliente),
    fuente: FuenteGoogleSheets = Depends(obtener_fuente),
):
    """Paquete completo de registros limpios para el dashboard."""
    try:
        filas_insp = fuente.leer_tabla(cliente.pestana_inspeccion)
        filas_def = fuente.leer_tabla(cliente.pestana_defectos)
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error))
    except gspread.exceptions.WorksheetNotFound as error:
        raise HTTPException(status_code=500, detail=f"No existe la pestaña {error}")
    except gspread.exceptions.APIError as error:
        raise HTTPException(status_code=502, detail=f"Google respondió con error: {error}")

    paquete = inspeccion.construir_paquete(filas_insp, filas_def)
    paquete["cliente"] = cliente.nombre
    return paquete
