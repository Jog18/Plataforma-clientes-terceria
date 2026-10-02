"""Hash y verificación de contraseñas con Argon2id.

Nunca se guarda una contraseña: se guarda su hash. Un hash Argon2id se ve así:
    $argon2id$v=19$m=65536,t=3,p=4$<sal>$<resultado>
Incluye la sal (aleatoria en cada hash) y los parámetros, así que dos hashes de
la misma contraseña salen distintos y no se puede "regresar" a la contraseña.
Argon2id está hecho para ser lento y gastar memoria, lo que vuelve carísimo
probar millones de contraseñas si alguien se roba el hash.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Parámetros recomendados por argon2-cffi (RFC 9106, perfil de bajo consumo).
_hasher = PasswordHasher()

LONGITUD_MINIMA = 12


def generar_hash(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar(hash_guardado: str, contrasena: str) -> bool:
    """True si la contraseña corresponde al hash. Nunca lanza excepción."""
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except (VerificationError, InvalidHashError):
        return False


def es_hash_valido(texto: str) -> bool:
    """Revisa que un texto tenga forma de hash Argon2id (para validar la config)."""
    try:
        _hasher.check_needs_rehash(texto)  # falla si no se puede interpretar
    except (InvalidHashError, ValueError):
        return False
    return texto.startswith("$argon2id$")
