"""Paso 1 de la Fase 3: configuración segura, cabeceras y hash de contraseñas."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Config
from app.seguridad.cabeceras import CabecerasSeguridad
from app.seguridad.contrasenas import es_hash_valido, generar_hash, verificar

BACKEND = Path(__file__).resolve().parents[1]
HASH = generar_hash("una-contraseña-larga")
LLAVE = "x" * 48


def crear_config(**valores) -> Config:
    # _env_file=None: que un .env local no cambie el resultado de la prueba.
    return Config(_env_file=None, **valores)


# ---- contraseñas ----------------------------------------------------------

def test_hash_verifica_solo_la_contrasena_correcta():
    assert verificar(HASH, "una-contraseña-larga")
    assert not verificar(HASH, "otra-contraseña")
    assert not verificar("no-es-un-hash", "una-contraseña-larga")


def test_hash_es_distinto_cada_vez():
    assert generar_hash("igual-igual-igual") != generar_hash("igual-igual-igual")


def test_reconoce_hash_argon2id():
    assert es_hash_valido(HASH)
    assert not es_hash_valido("")
    assert not es_hash_valido("contraseña-en-texto-plano")


# ---- configuración --------------------------------------------------------

def test_produccion_completa_arranca():
    c = crear_config(entorno="produccion", secret_key=LLAVE,
                     admin_usuario="admin", admin_hash=HASH)
    assert c.produccion


@pytest.mark.parametrize("quitar", ["secret_key", "admin_usuario", "admin_hash"])
def test_produccion_sin_secretos_no_arranca(quitar):
    valores = dict(entorno="produccion", secret_key=LLAVE,
                   admin_usuario="admin", admin_hash=HASH)
    valores[quitar] = ""
    with pytest.raises(ValueError, match="insegura"):
        crear_config(**valores)


def test_produccion_rechaza_llave_corta_y_hash_falso():
    with pytest.raises(ValueError):
        crear_config(entorno="produccion", secret_key="corta",
                     admin_usuario="admin", admin_hash=HASH)
    with pytest.raises(ValueError):
        crear_config(entorno="produccion", secret_key=LLAVE,
                     admin_usuario="admin", admin_hash="mi-contraseña")


def test_desarrollo_inventa_llave_temporal():
    c = crear_config()
    assert not c.produccion
    assert len(c.secret_key) >= 32


def test_hash_con_comillas_simples_en_env(tmp_path):
    # El hash trae signos $; con comillas simples el .env lo lee tal cual.
    env = tmp_path / ".env"
    env.write_text(f"ADMIN_USUARIO=admin\nADMIN_HASH='{HASH}'\n", encoding="utf-8")
    c = Config(_env_file=env)
    assert c.admin_hash == HASH


# ---- cabeceras ------------------------------------------------------------

def app_de_prueba(produccion: bool) -> TestClient:
    app = FastAPI()
    app.add_middleware(CabecerasSeguridad, produccion=produccion)

    @app.get("/api/algo")
    def algo():
        return {"ok": True}

    @app.get("/pagina")
    def pagina():
        return {"ok": True}

    return TestClient(app)


def test_cabeceras_en_desarrollo():
    r = app_de_prueba(produccion=False).get("/pagina")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in r.headers
    assert "no-store" not in r.headers.get("Cache-Control", "")


def test_api_no_se_guarda_en_cache():
    r = app_de_prueba(produccion=False).get("/api/algo")
    assert r.headers["Cache-Control"] == "no-store"


def test_hsts_solo_en_produccion():
    r = app_de_prueba(produccion=True).get("/pagina")
    assert r.headers["Strict-Transport-Security"].startswith("max-age=31536000")


# ---- la app real ----------------------------------------------------------

def correr_en_entorno(codigo: str, **variables) -> subprocess.CompletedProcess:
    # Proceso aparte: config se crea al importar, y así cada prueba ve su entorno.
    env = {k: v for k, v in os.environ.items()
           if k.upper() not in {"ENTORNO", "SECRET_KEY", "ADMIN_USUARIO", "ADMIN_HASH"}}
    env.update(variables)
    return subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=env,
                          capture_output=True, text=True)


VER_DOCS = (
    "from fastapi.testclient import TestClient;"
    "from app.main import app;"
    "c = TestClient(app);"
    "print(c.get('/docs').status_code, c.get('/openapi.json').status_code,"
    " c.get('/api/salud').status_code)"
)


def test_docs_apagado_en_produccion():
    r = correr_en_entorno(VER_DOCS, ENTORNO="produccion", SECRET_KEY=LLAVE,
                          ADMIN_USUARIO="admin", ADMIN_HASH=HASH)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["404", "404", "200"]


def test_docs_disponible_en_desarrollo():
    r = correr_en_entorno(VER_DOCS, ENTORNO="desarrollo")
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["200", "200", "200"]


def test_produccion_sin_secretos_no_levanta_la_app():
    r = correr_en_entorno("import app.main", ENTORNO="produccion")
    assert r.returncode != 0
    assert "insegura" in r.stderr
