"""Paso 2 de la Fase 3: login, sesiones, límite de intentos y rutas protegidas."""

import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
CONTRASENA = "contraseña-de-prueba-123"


@pytest.fixture(scope="module")
def cliente():
    """Un TestClient con un admin de prueba, sin leer el .env de la máquina."""
    from app.seguridad.contrasenas import generar_hash

    entorno_previo = dict(os.environ)
    os.environ.update({
        "ENTORNO": "desarrollo",
        "SECRET_KEY": "llave-de-pruebas-" + "x" * 32,
        "ADMIN_USUARIO": "admin",
        "ADMIN_HASH": generar_hash(CONTRASENA),
        "INTENTOS_MAXIMOS": "3",
        "BLOQUEO_MINUTOS": "15",
    })
    # Importar después de fijar el entorno: config se construye al importar.
    for modulo in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[modulo]
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c

    # Dejar el entorno como estaba para no afectar a los demás archivos de prueba.
    os.environ.clear()
    os.environ.update(entorno_previo)


def entrar(cliente, usuario="admin", contrasena=CONTRASENA):
    return cliente.post("/api/login", json={"usuario": usuario, "contrasena": contrasena})


@pytest.fixture(autouse=True)
def sin_sesion_ni_bloqueos(cliente):
    cliente.cookies.clear()
    from app.dependencias import intentos
    intentos._fallos.clear()


# ---- rutas protegidas -------------------------------------------------------

def test_datos_sin_sesion_da_401(cliente):
    assert cliente.get("/api/datos").status_code == 401
    assert cliente.get("/api/yo").status_code == 401


def test_raiz_sin_sesion_redirige_a_login(cliente):
    r = cliente.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_salud_sigue_publica(cliente):
    assert cliente.get("/api/salud").status_code == 200


# ---- login ------------------------------------------------------------------

def test_login_correcto_crea_cookie_segura(cliente):
    r = entrar(cliente)
    assert r.status_code == 200
    assert r.json() == {"usuario": "admin", "rol": "admin"}
    cookie = r.headers["set-cookie"].lower()
    assert "sesion=" in cookie and "httponly" in cookie and "samesite=strict" in cookie
    assert "secure" not in cookie  # en desarrollo no hay HTTPS

    assert cliente.get("/api/yo").json()["usuario"] == "admin"
    r = cliente.get("/", follow_redirects=False)
    assert r.status_code == 200
    assert cliente.get("/login", follow_redirects=False).status_code == 303


@pytest.mark.parametrize("usuario, contrasena", [
    ("admin", "contraseña-mala"),
    ("nadie", CONTRASENA),
    ("Admin", CONTRASENA),  # mayúsculas: usuario distinto
])
def test_login_incorrecto_mismo_mensaje(cliente, usuario, contrasena):
    r = entrar(cliente, usuario, contrasena)
    assert r.status_code == 401
    assert r.json()["detail"] == "Usuario o contraseña incorrectos"
    assert "set-cookie" not in r.headers


def test_login_rechaza_datos_incompletos(cliente):
    assert cliente.post("/api/login", json={"usuario": "admin"}).status_code == 422


def test_login_rechaza_otro_origen(cliente):
    r = cliente.post("/api/login", json={"usuario": "admin", "contrasena": CONTRASENA},
                     headers={"Origin": "https://sitio-malo.com"})
    assert r.status_code == 403


def test_login_acepta_mismo_origen(cliente):
    r = cliente.post("/api/login", json={"usuario": "admin", "contrasena": CONTRASENA},
                     headers={"Origin": "http://testserver"})
    assert r.status_code == 200


# ---- límite de intentos ------------------------------------------------------

def test_bloqueo_tras_intentos_fallidos(cliente):
    for _ in range(3):
        assert entrar(cliente, contrasena="mala").status_code == 401
    r = entrar(cliente)  # contraseña correcta, pero ya bloqueado
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_login_correcto_limpia_el_contador(cliente):
    for _ in range(2):
        entrar(cliente, contrasena="mala")
    assert entrar(cliente).status_code == 200
    cliente.cookies.clear()
    for _ in range(2):
        entrar(cliente, contrasena="mala")
    assert entrar(cliente).status_code == 200  # no se acumularon los de antes


# ---- sesiones ------------------------------------------------------------

def test_cookie_alterada_se_rechaza(cliente):
    entrar(cliente)
    valida = cliente.cookies.get("sesion")
    cliente.cookies.set("sesion", valida[:-3] + "abc")
    assert cliente.get("/api/yo").status_code == 401


def test_cookie_vencida_se_rechaza(cliente):
    from app.dependencias import sesiones
    entrar(cliente)
    original = sesiones.segundos
    sesiones.segundos = -1  # todo lo firmado "ya venció"
    try:
        assert cliente.get("/api/yo").status_code == 401
    finally:
        sesiones.segundos = original


def test_cambiar_contrasena_cierra_sesiones(cliente):
    from app.config import config
    from app.seguridad.contrasenas import generar_hash
    entrar(cliente)
    hash_anterior = config.admin_hash
    config.admin_hash = generar_hash("otra-contraseña-nueva")
    try:
        assert cliente.get("/api/yo").status_code == 401
    finally:
        config.admin_hash = hash_anterior


def test_logout_borra_la_cookie(cliente):
    entrar(cliente)
    r = cliente.post("/api/logout")
    assert r.status_code == 204
    assert 'sesion=""' in r.headers["set-cookie"] or "max-age=0" in r.headers["set-cookie"].lower()
    assert cliente.get("/api/yo").status_code == 401
