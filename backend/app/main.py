"""Punto de entrada del servidor.

Arrancar en tu máquina (desde la raíz del proyecto):
    uvicorn app.main:app --reload --app-dir backend

Luego abre http://127.0.0.1:8000/docs para probar las rutas (en producción
/docs está apagado para no exponer el mapa de la API).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import RAIZ_PROYECTO, config
from app.routers import datos
from app.seguridad.cabeceras import CabecerasSeguridad

app = FastAPI(
    title="Plataforma Clientes Tercería",
    description="Dashboard de calidad en tiempo real a partir de Google Sheets.",
    version="0.1.0",
    docs_url=None if config.produccion else "/docs",
    redoc_url=None if config.produccion else "/redoc",
    openapi_url=None if config.produccion else "/openapi.json",
)

# Cabeceras de seguridad en todas las respuestas (ver seguridad/cabeceras.py).
app.add_middleware(CabecerasSeguridad, produccion=config.produccion)

# Cada router se registra aquí. Mañana: app.include_router(auth.router), etc.
app.include_router(datos.router)

# El frontend (Fase 3) vivirá en /frontend y se sirve desde el mismo servidor.
FRONTEND = RAIZ_PROYECTO / "frontend"
INDEX = FRONTEND / "index.html"


@app.get("/", include_in_schema=False)
def inicio():
    if INDEX.exists():
        return FileResponse(INDEX)
    return JSONResponse({
        "mensaje": "Backend activo. El dashboard llega en la Fase 3.",
        "rutas": ["/api/salud", "/api/datos", "/docs"],
    })


if FRONTEND.exists():
    # /css/estilos.css, /js/app.js, etc.
    app.mount("/", StaticFiles(directory=FRONTEND), name="frontend")
