"""Configuración del backend.

Todo lo que puede cambiar entre tu computadora y Render (rutas, IDs, tiempos)
vive aquí y se lee de variables de entorno. En tu máquina puedes ponerlas en
un archivo `.env` en la raíz del proyecto (está en .gitignore); en Render se
capturan en el panel de "Environment". Si no defines nada, se usan los valores
por defecto, que son los de hoy.

Uso en el resto del código:
    from app.config import config
    config.sheet_id
"""

import logging
import secrets
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raíz del repositorio (dos niveles arriba de backend/app/).
RAIZ_PROYECTO = Path(__file__).resolve().parents[2]


class Config(BaseSettings):
    # ID de la hoja "prueba" de HBPO. No es secreto: sin el robot no sirve.
    sheet_id: str = "1Bmzr7_F1GXc7204Jtu8rtUkE7RaxsGFsjGSPDR-f-GA"

    # Llave JSON del robot. En Render será un "Secret File" y aquí se pone su ruta.
    credenciales: Path = RAIZ_PROYECTO / "backend" / "credenciales.json"

    # Cuántos segundos se guardan en memoria los datos leídos de Google antes
    # de volver a pedirlos. Protege la cuota de lectura de la API de Sheets.
    cache_segundos: int = 300

    # El botón "Actualizar" fuerza una lectura nueva, pero no más seguido que
    # esto (segundos): protege la cuota de Google si se pulsa muchas veces.
    refresco_minimo_segundos: int = 10

    # Pestañas que usa el dashboard.
    pestana_inspeccion: str = "Inspeccion HBPO"
    pestana_defectos: str = "Detalle Defectos"

    # ---- seguridad (Fase 3) ------------------------------------------------

    # "desarrollo" en tu máquina, "produccion" en Render. En producción se
    # apaga /docs, se activa HSTS y se exige que existan todos los secretos.
    entorno: Literal["desarrollo", "produccion"] = "desarrollo"

    # Llave con la que se firman las cookies de sesión. Quien la tenga puede
    # fabricar sesiones, así que es secreta. Genérala con:
    #     python backend/scripts/crear_hash.py --secret-key
    secret_key: str = ""

    # Usuario administrador. El hash sale de backend/scripts/crear_hash.py;
    # la contraseña en texto plano nunca se escribe en ningún archivo.
    admin_usuario: str = ""
    admin_hash: str = ""

    # Duración de la sesión y límite de intentos fallidos de login.
    sesion_horas: int = 8
    intentos_maximos: int = 5
    bloqueo_minutos: int = 15

    @property
    def produccion(self) -> bool:
        return self.entorno == "produccion"

    @model_validator(mode="after")
    def _revisar_seguridad(self) -> "Config":
        # Importación aquí para no cargar argon2 si nadie usa la config.
        from app.seguridad.contrasenas import es_hash_valido

        if self.produccion:
            # Mejor que el servidor no arranque a que se publique sin protección.
            faltan = []
            if len(self.secret_key) < 32:
                faltan.append("SECRET_KEY (mínimo 32 caracteres)")
            if not self.admin_usuario:
                faltan.append("ADMIN_USUARIO")
            if not es_hash_valido(self.admin_hash):
                faltan.append("ADMIN_HASH (hash Argon2id de crear_hash.py)")
            if faltan:
                raise ValueError(
                    "Configuración insegura para producción. Falta o es inválido: "
                    + ", ".join(faltan)
                )
        else:
            if not self.secret_key:
                # En tu máquina se inventa una llave al arrancar: funciona,
                # pero las sesiones se pierden cada vez que reinicias.
                self.secret_key = secrets.token_urlsafe(48)
                logging.getLogger(__name__).warning(
                    "SECRET_KEY no definida: se usa una temporal (solo desarrollo)."
                )
            if self.admin_hash and not es_hash_valido(self.admin_hash):
                raise ValueError("ADMIN_HASH no es un hash Argon2id válido.")
        return self

    @field_validator("credenciales")
    @classmethod
    def _ruta_desde_la_raiz(cls, ruta: Path) -> Path:
        # Si en .env pones una ruta relativa (backend/credenciales.json), se
        # entiende desde la raíz del proyecto, no desde donde ejecutes.
        return ruta if ruta.is_absolute() else RAIZ_PROYECTO / ruta

    # Cómo se leen las variables: de un archivo .env o del entorno, sin
    # distinguir mayúsculas (SHEET_ID y sheet_id son lo mismo).
    model_config = SettingsConfigDict(
        env_file=RAIZ_PROYECTO / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Una sola instancia para todo el backend.
config = Config()
