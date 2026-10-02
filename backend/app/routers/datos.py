"""Rutas de datos del dashboard.

Un "router" es un grupo de rutas con un prefijo común (/api). main.py lo
registra en la app. Las rutas de login viven en routers/auth.py.

/api/datos exige sesión: `obtener_cliente` depende de `usuario_actual`, que
responde 401 si no hay cookie válida. /api/salud sigue pública porque Render
la usa para vigilar el servicio.
"""

import gspread
from fastapi import APIRouter, Depends, HTTPException

from app.clientes import Cliente
from app.config import config
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
