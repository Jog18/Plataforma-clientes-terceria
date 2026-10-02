"""Rutas de inicio y cierre de sesión.

    POST /api/login   {usuario, contrasena} -> cookie de sesión + datos del usuario
    POST /api/logout                        -> borra la cookie
    GET  /api/yo                            -> quién soy (401 si no hay sesión)

Defensas en /api/login:
- Límite de intentos por IP y por usuario (429 mientras dure el bloqueo).
- Se verifica la contraseña aunque el usuario no exista (contra un hash de
  relleno), para que el tiempo de respuesta no revele qué usuarios existen.
- Un solo mensaje de error, sin decir si falló el usuario o la contraseña.
- Solo se acepta JSON, y la cabecera Origin (si viene) debe ser la nuestra:
  un formulario HTML de otro sitio no puede disparar un login.
- Cada fallo queda en el log con usuario e IP, nunca con la contraseña.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.dependencias import intentos, ip_del_visitante, sesiones, usuario_actual
from app.esquemas import DatosLogin, UsuarioActual
from app.seguridad.contrasenas import generar_hash, verificar
from app.seguridad.sesiones import Sesion, huella_de
from app.usuarios import Usuario, buscar_usuario

router = APIRouter(prefix="/api", tags=["auth"])
log = logging.getLogger(__name__)

# Hash de relleno para cuando el usuario no existe (ver docstring).
_HASH_RELLENO = generar_hash("relleno-para-tiempo-constante")


def _mismo_origen(request: Request) -> bool:
    origen = request.headers.get("origin")
    if origen is None:
        return True  # peticiones sin Origin (curl, misma página en navegadores viejos)
    base = f"{request.url.scheme}://{request.url.netloc}"
    # Detrás del proxy de Render el esquema interno es http aunque el
    # navegador usó https; se compara solo el host.
    return origen.split("://", 1)[-1] == base.split("://", 1)[-1]


@router.post("/login", response_model=UsuarioActual)
def login(datos: DatosLogin, request: Request, respuesta: Response):
    if not _mismo_origen(request):
        raise HTTPException(status_code=403, detail="Origen no permitido")

    ip = ip_del_visitante(request)
    llave_ip = f"ip:{ip}"
    llave_usuario = f"usuario:{datos.usuario.strip()}"

    espera = max(intentos.segundos_de_bloqueo(llave_ip),
                 intentos.segundos_de_bloqueo(llave_usuario))
    if espera:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos. Espera {max(1, espera // 60)} minuto(s).",
            headers={"Retry-After": str(espera)},
        )

    usuario = buscar_usuario(datos.usuario)
    hash_a_probar = usuario.hash_contrasena if usuario else _HASH_RELLENO
    correcto = verificar(hash_a_probar, datos.contrasena) and usuario is not None

    if not correcto:
        intentos.registrar_fallo(llave_ip)
        intentos.registrar_fallo(llave_usuario)
        log.warning("Login fallido: usuario=%r ip=%s", datos.usuario, ip)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    intentos.limpiar(llave_ip)
    intentos.limpiar(llave_usuario)
    sesiones.iniciar(respuesta, Sesion(
        usuario=usuario.nombre, rol=usuario.rol,
        huella=huella_de(usuario.hash_contrasena),
    ))
    log.info("Login correcto: usuario=%r ip=%s", usuario.nombre, ip)
    return UsuarioActual(usuario=usuario.nombre, rol=usuario.rol)


@router.post("/logout", status_code=204)
def logout(request: Request, respuesta: Response):
    if not _mismo_origen(request):
        raise HTTPException(status_code=403, detail="Origen no permitido")
    sesiones.cerrar(respuesta)
    return Response(status_code=204, headers=respuesta.headers)


@router.get("/yo", response_model=UsuarioActual)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return UsuarioActual(usuario=usuario.nombre, rol=usuario.rol)
