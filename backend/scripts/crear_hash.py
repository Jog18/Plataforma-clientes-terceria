"""Genera los secretos del login sin escribirlos en ningún archivo.

Uso (desde la carpeta raíz del proyecto):

    python backend/scripts/crear_hash.py
        Pide la contraseña del administrador dos veces (no se ve al teclear)
        y muestra su hash Argon2id. Copia la línea ADMIN_HASH=... a tu .env
        y, sin las comillas, al panel Environment de Render.

    python backend/scripts/crear_hash.py --secret-key
        Muestra una SECRET_KEY aleatoria para firmar las cookies de sesión.
        Usa una distinta en tu máquina y en Render.

La contraseña nunca se guarda: solo pasa por la memoria de este programa.
"""

import getpass
import secrets
import sys
from pathlib import Path

# Para poder importar app.* al correr el script directamente.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seguridad.contrasenas import LONGITUD_MINIMA, generar_hash  # noqa: E402


def pedir_contrasena() -> str:
    while True:
        primera = getpass.getpass("Contraseña del administrador: ")
        if len(primera) < LONGITUD_MINIMA:
            print(f"Debe tener al menos {LONGITUD_MINIMA} caracteres. Intenta de nuevo.\n")
            continue
        if getpass.getpass("Repítela: ") != primera:
            print("No coinciden. Intenta de nuevo.\n")
            continue
        return primera


def main():
    if "--secret-key" in sys.argv[1:]:
        print(f"SECRET_KEY={secrets.token_urlsafe(48)}")
        return

    contrasena = pedir_contrasena()
    print("\nCopia esta línea en tu .env (con las comillas simples):\n")
    print(f"ADMIN_HASH='{generar_hash(contrasena)}'")
    print("\nEn Render pega solo el valor, sin las comillas.")


if __name__ == "__main__":
    main()
