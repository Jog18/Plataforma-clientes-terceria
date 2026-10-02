"""Sesiones en cookie firmada.

Al iniciar sesión, el servidor mete en una cookie un pequeño paquete
(usuario, rol y una "huella" de su contraseña) firmado con SECRET_KEY. El
navegador lo manda en cada petición y el servidor comprueba la firma: si
alguien cambió una letra, la firma no coincide y la sesión se rechaza. No
hace falta guardar nada en el servidor, lo que encaja con Render (sin disco
persistente).

Protecciones de la cookie:
    HttpOnly   JavaScript no la puede leer (frena robo por XSS).
    Secure     solo viaja por HTTPS (en producción).
    SameSite   Strict: otro sitio no puede mandarla (frena CSRF).
    max_age    caduca sola; itsdangerous también rechaza firmas viejas.

La huella es un pedazo del hash de la contraseña: si el admin cambia su
contraseña, todas las sesiones anteriores dejan de servir.
"""

import hashlib
from dataclasses import dataclass

from fastapi import Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

NOMBRE_COOKIE = "sesion"


@dataclass(frozen=True)
class Sesion:
    usuario: str
    rol: str
    huella: str


def huella_de(hash_contrasena: str) -> str:
    """Identificador corto del hash de la contraseña (no revela el hash)."""
    return hashlib.sha256(hash_contrasena.encode()).hexdigest()[:16]


class GestorSesiones:
    def __init__(self, secret_key: str, horas: int, produccion: bool):
        self._firmador = URLSafeTimedSerializer(secret_key, salt="sesion-v1")
        self.segundos = horas * 3600
        self.produccion = produccion

    # ---- crear / borrar -------------------------------------------------

    def iniciar(self, respuesta: Response, sesion: Sesion) -> None:
        valor = self._firmador.dumps(
            {"u": sesion.usuario, "r": sesion.rol, "h": sesion.huella}
        )
        respuesta.set_cookie(
            key=NOMBRE_COOKIE,
            value=valor,
            max_age=self.segundos,
            httponly=True,
            secure=self.produccion,
            samesite="strict",
            path="/",
        )

    def cerrar(self, respuesta: Response) -> None:
        respuesta.delete_cookie(
            key=NOMBRE_COOKIE, path="/", httponly=True,
            secure=self.produccion, samesite="strict",
        )

    # ---- leer ------------------------------------------------------------

    def leer(self, valor_cookie: str | None) -> Sesion | None:
        """Regresa la sesión si la cookie es auténtica y vigente; si no, None."""
        if not valor_cookie:
            return None
        try:
            datos = self._firmador.loads(valor_cookie, max_age=self.segundos)
        except (BadSignature, SignatureExpired):
            return None
        try:
            return Sesion(usuario=datos["u"], rol=datos["r"], huella=datos["h"])
        except (KeyError, TypeError):
            return None
