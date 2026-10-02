"""Dependencias de FastAPI.

Una dependencia es una función que FastAPI ejecuta antes de la ruta y cuyo
resultado le entrega como parámetro (`Depends`). Aquí se concentran las
preguntas "¿quién pide?", "¿qué cliente pide?" y "¿de dónde saco sus datos?".

Cadena para una petición a /api/datos:
    usuario_actual  -> lee la cookie, valida firma y vigencia; 401 si no hay.
    obtener_cliente -> qué cliente quiere ver y si tiene permiso; 403 si no.
    obtener_fuente  -> la conexión (con caché) a la hoja de ese cliente.
"""

from fastapi import Cookie, Depends, HTTPException, Request

from app.clientes import CLIENTE_POR_DEFECTO, CLIENTES, Cliente
from app.config import config
from app.fuentes.gsheets import FuenteGoogleSheets
from app.seguridad.intentos import LimiteIntentos
from app.seguridad.sesiones import NOMBRE_COOKIE, GestorSesiones, Sesion, huella_de
from app.usuarios import Usuario, buscar_usuario

# Objetos compartidos entre todas las peticiones.
sesiones = GestorSesiones(
    secret_key=config.secret_key,
    horas=config.sesion_horas,
    produccion=config.produccion,
)
intentos = LimiteIntentos(
    maximo=config.intentos_maximos,
    bloqueo_minutos=config.bloqueo_minutos,
)
_fuentes: dict[str, FuenteGoogleSheets] = {}


# ---- quién pide -----------------------------------------------------------

def ip_del_visitante(request: Request) -> str:
    """IP real del visitante. En Render llega por X-Forwarded-For.

    Solo se confía en esa cabecera en producción (detrás del proxy de Render);
    en tu máquina cualquiera podría inventarla.
    """
    if config.produccion:
        reenviada = request.headers.get("x-forwarded-for", "")
        if reenviada:
            return reenviada.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


def sesion_actual(sesion: str | None = Cookie(default=None, alias=NOMBRE_COOKIE)) -> Sesion | None:
    """La sesión de la cookie, o None si no hay o no es válida. Nunca falla."""
    return sesiones.leer(sesion)


def usuario_actual(sesion: Sesion | None = Depends(sesion_actual)) -> Usuario:
    """El usuario con sesión válida. 401 si no hay sesión o ya no sirve."""
    if sesion is None:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar")
    usuario = buscar_usuario(sesion.usuario)
    # Si el usuario desapareció o cambió su contraseña, la sesión vieja muere.
    if usuario is None or huella_de(usuario.hash_contrasena) != sesion.huella:
        raise HTTPException(status_code=401, detail="La sesión ya no es válida")
    return usuario


# ---- qué cliente ----------------------------------------------------------

def obtener_cliente(usuario: Usuario = Depends(usuario_actual)) -> Cliente:
    clave = CLIENTE_POR_DEFECTO
    cliente = CLIENTES.get(clave)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no configurado")
    if not usuario.puede_ver(clave):
        raise HTTPException(status_code=403, detail="No tienes acceso a este cliente")
    return cliente


# ---- de dónde salen los datos ----------------------------------------------

def obtener_fuente(cliente: Cliente = Depends(obtener_cliente)) -> FuenteGoogleSheets:
    if cliente.sheet_id not in _fuentes:
        _fuentes[cliente.sheet_id] = FuenteGoogleSheets(
            sheet_id=cliente.sheet_id,
            credenciales=config.credenciales,
            cache_segundos=config.cache_segundos,
        )
    return _fuentes[cliente.sheet_id]
