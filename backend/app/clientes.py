"""Catálogo de clientes.

Hoy solo existe HBPO. Cuando entre otro cliente se agrega una entrada aquí
(con su hoja y sus pestañas) y el resto del backend ya sabe qué hacer.
Más adelante este catálogo puede vivir en una base de datos.
"""

from dataclasses import dataclass

from app.config import config


@dataclass(frozen=True)
class Cliente:
    clave: str               # identificador corto, para URLs y sesiones
    nombre: str              # como se muestra en pantalla
    sheet_id: str
    pestana_inspeccion: str
    pestana_defectos: str


CLIENTES: dict[str, Cliente] = {
    "hbpo": Cliente(
        clave="hbpo",
        nombre="HBPO",
        sheet_id=config.sheet_id,
        pestana_inspeccion=config.pestana_inspeccion,
        pestana_defectos=config.pestana_defectos,
    ),
}

CLIENTE_POR_DEFECTO = "hbpo"
