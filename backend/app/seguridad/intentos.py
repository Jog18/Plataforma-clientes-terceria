"""Límite de intentos fallidos de inicio de sesión (fuerza bruta).

Lleva la cuenta de fallos por "llave" (la IP del visitante y, aparte, el
nombre de usuario). Al llegar al máximo dentro de la ventana, esa llave
queda bloqueada durante `bloqueo_minutos`, aunque la contraseña siguiente
sea correcta. Un login correcto limpia el contador de esa llave.

Vive en memoria: basta para un solo servidor en Render. Si algún día hay
varios, se cambia por una tabla en la base de datos o Redis con la misma
interfaz (esta_bloqueado / registrar_fallo / limpiar).
"""

import threading
import time
from collections import deque


class LimiteIntentos:
    def __init__(self, maximo: int, bloqueo_minutos: int):
        self.maximo = maximo
        self.ventana = bloqueo_minutos * 60
        # llave -> momentos (monotonic) de los últimos fallos.
        self._fallos: dict[str, deque[float]] = {}
        self._candado = threading.Lock()

    def _vigentes(self, llave: str, ahora: float) -> deque[float]:
        cola = self._fallos.setdefault(llave, deque())
        while cola and ahora - cola[0] > self.ventana:
            cola.popleft()
        if not cola:
            self._fallos.pop(llave, None)
        return cola

    def segundos_de_bloqueo(self, llave: str) -> int:
        """0 si puede intentar; si no, cuántos segundos faltan para poder."""
        ahora = time.monotonic()
        with self._candado:
            cola = self._vigentes(llave, ahora)
            if len(cola) < self.maximo:
                return 0
            return max(1, int(self.ventana - (ahora - cola[0])))

    def esta_bloqueado(self, llave: str) -> bool:
        return self.segundos_de_bloqueo(llave) > 0

    def registrar_fallo(self, llave: str) -> None:
        ahora = time.monotonic()
        with self._candado:
            self._vigentes(llave, ahora)
            self._fallos.setdefault(llave, deque()).append(ahora)

    def limpiar(self, llave: str) -> None:
        with self._candado:
            self._fallos.pop(llave, None)
