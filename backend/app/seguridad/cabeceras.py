"""Cabeceras HTTP de seguridad que se agregan a todas las respuestas.

Son instrucciones para el navegador:
- Content-Security-Policy: solo se ejecuta JavaScript y CSS servidos por
  nuestro propio sitio; nada de scripts metidos dentro del HTML ni de otros
  dominios. Si alguien lograra colar código en un comentario de la hoja, el
  navegador se negaría a ejecutarlo.
- X-Frame-Options / frame-ancestors: nadie puede incrustar el dashboard en
  otra página (evita que engañen al usuario para que haga clic sin saber).
- X-Content-Type-Options: el navegador no "adivina" tipos de archivo.
- Referrer-Policy: no se filtra nuestra URL a otros sitios.
- Permissions-Policy: la página no puede pedir cámara, micrófono ni ubicación.
- Strict-Transport-Security (solo producción): el navegador recordará usar
  siempre HTTPS con este sitio durante un año.
- Cache-Control: no-store en /api: los datos no se quedan guardados en la
  caché del navegador de una computadora compartida.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

CABECERAS_FIJAS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# La documentación interactiva (/docs) carga Swagger desde un CDN y usa
# scripts en línea; con la CSP estricta no funcionaría. Solo existe en
# desarrollo, así que ahí se le deja sin CSP.
RUTAS_SIN_CSP = ("/docs", "/redoc", "/openapi.json")


class CabecerasSeguridad(BaseHTTPMiddleware):
    def __init__(self, app, produccion: bool):
        super().__init__(app)
        self.produccion = produccion

    async def dispatch(self, request: Request, call_next):
        respuesta = await call_next(request)
        ruta = request.url.path

        for nombre, valor in CABECERAS_FIJAS.items():
            respuesta.headers.setdefault(nombre, valor)

        if not ruta.startswith(RUTAS_SIN_CSP):
            respuesta.headers.setdefault("Content-Security-Policy", CSP)

        if ruta.startswith("/api/"):
            respuesta.headers["Cache-Control"] = "no-store"

        if self.produccion:
            respuesta.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return respuesta
