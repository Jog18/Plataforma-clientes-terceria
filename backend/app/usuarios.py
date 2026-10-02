"""De dónde salen los usuarios.

Hoy existe un solo usuario, el administrador, definido en variables de
entorno (ADMIN_USUARIO y ADMIN_HASH). El resto del backend solo llama a
`buscar_usuario(nombre)`; cuando haya base de datos con usuarios por
cliente, se reescribe esta función y nada más cambia.

Roles:
    admin    ve todos los clientes (hoy: HBPO).
    cliente  (futuro) ve solo su empresa, según `clientes`.
"""

from dataclasses import dataclass, field

from app.config import config

ROL_ADMIN = "admin"
ROL_CLIENTE = "cliente"


@dataclass(frozen=True)
class Usuario:
    nombre: str
    hash_contrasena: str
    rol: str
    clientes: tuple[str, ...] = field(default_factory=tuple)  # claves de clientes.py

    def puede_ver(self, clave_cliente: str) -> bool:
        return self.rol == ROL_ADMIN or clave_cliente in self.clientes


def buscar_usuario(nombre: str) -> Usuario | None:
    nombre = nombre.strip()
    if not nombre or not config.admin_usuario or not config.admin_hash:
        return None
    # Comparación exacta: "Admin" y "admin" son usuarios distintos.
    if nombre != config.admin_usuario:
        return None
    return Usuario(nombre=nombre, hash_contrasena=config.admin_hash, rol=ROL_ADMIN)
