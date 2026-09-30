"""Dependencias de FastAPI.

Una dependencia es una función que FastAPI ejecuta antes de la ruta y cuyo
resultado le entrega como parámetro (`Depends`). Aquí se concentran las
preguntas "¿qué cliente pide?" y "¿de dónde saco sus datos?".

Hoy la respuesta a la primera es siempre HBPO. Cuando haya inicio de sesión,
`obtener_cliente` leerá el usuario de la sesión y validará que tenga permiso
sobre ese cliente; las rutas no cambian.
"""

from fastapi import Depends, HTTPException

from app.clientes import CLIENTE_POR_DEFECTO, CLIENTES, Cliente
from app.config import config
from app.fuentes.gsheets import FuenteGoogleSheets

# Una fuente (con su caché) por hoja, compartida entre todas las peticiones.
_fuentes: dict[str, FuenteGoogleSheets] = {}


def obtener_cliente() -> Cliente:
    cliente = CLIENTES.get(CLIENTE_POR_DEFECTO)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no configurado")
    return cliente


def obtener_fuente(cliente: Cliente = Depends(obtener_cliente)) -> FuenteGoogleSheets:
    if cliente.sheet_id not in _fuentes:
        _fuentes[cliente.sheet_id] = FuenteGoogleSheets(
            sheet_id=cliente.sheet_id,
            credenciales=config.credenciales,
            cache_segundos=config.cache_segundos,
        )
    return _fuentes[cliente.sheet_id]
