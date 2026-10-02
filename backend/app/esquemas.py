"""Modelos Pydantic de entrada y salida de la API.

FastAPI los usa para validar lo que llega (si falta un campo o el tipo no
cuadra, responde 422 antes de ejecutar la ruta) y para documentar /docs.
"""

from pydantic import BaseModel, Field


class DatosLogin(BaseModel):
    usuario: str = Field(min_length=1, max_length=64)
    contrasena: str = Field(min_length=1, max_length=256)


class UsuarioActual(BaseModel):
    usuario: str
    rol: str
