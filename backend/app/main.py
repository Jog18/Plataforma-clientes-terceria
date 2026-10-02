"""Punto de entrada del servidor.

Arrancar en tu máquina (desde la raíz del proyecto):
    uvicorn app.main:app --reload --app-dir backend

Luego abre http://127.0.0.1:8000/docs para probar las rutas (en producción
/docs está apagado para no exponer el mapa de la API).
"""

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import RAIZ_PROYECTO, config
from app.dependencias import sesion_actual
from app.routers import auth, datos
from app.seguridad.cabeceras import CabecerasSeguridad
from app.seguridad.sesiones import Sesion

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

# Cada router se registra aquí.
app.include_router(auth.router)
app.include_router(datos.router)

# El frontend vive en /frontend y se sirve desde el mismo servidor.
FRONTEND = RAIZ_PROYECTO / "frontend"
INDEX = FRONTEND / "index.html"
LOGIN = FRONTEND / "login.html"


@app.get("/", include_in_schema=False)
def inicio(sesion: Sesion | None = Depends(sesion_actual)):
    """El dashboard. Sin sesión, manda a la pantalla de inicio de sesión."""
    if sesion is None:
        return RedirectResponse("/login", status_code=303)
    if INDEX.exists():
        return FileResponse(INDEX)
    return JSONResponse({
        "mensaje": f"Sesión iniciada como {sesion.usuario}. El dashboard llega en el paso 4.",
        "rutas": ["/api/datos", "/api/yo", "/api/logout"],
    })


@app.get("/login", include_in_schema=False)
def pantalla_login(sesion: Sesion | None = Depends(sesion_actual)):
    """La pantalla de inicio de sesión. Con sesión ya abierta, va al dashboard."""
    if sesion is not None:
        return RedirectResponse("/", status_code=303)
    if LOGIN.exists():
        return FileResponse(LOGIN)
    return JSONResponse({"mensaje": "Falta frontend/login.html."}, status_code=404)


if FRONTEND.exists():
    # Archivos estáticos (/css/..., /js/...). No contienen datos, así que son
    # públicos; index.html y login.html se sirven arriba, con sus reglas.
    app.mount("/", StaticFiles(directory=FRONTEND), name="frontend")
