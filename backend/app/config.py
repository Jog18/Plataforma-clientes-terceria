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

from pathlib import Path

from pydantic import field_validator
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

    # Pestañas que usa el dashboard.
    pestana_inspeccion: str = "Inspeccion HBPO"
    pestana_defectos: str = "Detalle Defectos"

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
