"""Fuente de datos: Google Sheets.

Este es el único archivo que habla con Google. El resto del backend le pide
"dame la pestaña X" y recibe una lista de diccionarios (una fila = un dict con
los encabezados como llaves). Si mañana los datos viven en una base de datos,
se escribe otra fuente con la misma función `leer_tabla` y nada más cambia.

Incluye una caché en memoria: la primera vez lee de Google, y durante
`cache_segundos` cualquier otra petición recibe la copia guardada. Así el
dashboard puede tener varios usuarios sin agotar la cuota de la API.
"""

import threading
import time
from pathlib import Path

import gspread


class FuenteGoogleSheets:
    def __init__(self, sheet_id: str, credenciales: Path, cache_segundos: int):
        self.sheet_id = sheet_id
        self.credenciales = credenciales
        self.cache_segundos = cache_segundos

        # La conexión se abre hasta la primera lectura, no al importar el
        # módulo, para que el servidor arranque aunque falte la llave.
        self._hoja: gspread.Spreadsheet | None = None

        # Caché: nombre de pestaña -> (momento de lectura, filas).
        self._cache: dict[str, tuple[float, list[dict]]] = {}

        # Si dos peticiones llegan al mismo tiempo con la caché vencida, el
        # candado evita que las dos vayan a Google; la segunda espera y usa
        # lo que trajo la primera.
        self._candado = threading.Lock()

    # ---- conexión --------------------------------------------------------

    def _abrir_hoja(self) -> gspread.Spreadsheet:
        if self._hoja is None:
            if not self.credenciales.exists():
                raise FileNotFoundError(
                    f"No encontré la llave del robot en {self.credenciales}"
                )
            cliente = gspread.service_account(filename=self.credenciales)
            self._hoja = cliente.open_by_key(self.sheet_id)
        return self._hoja

    # ---- lectura ---------------------------------------------------------

    def leer_tabla(self, pestana: str) -> list[dict]:
        """Regresa las filas de una pestaña como lista de diccionarios.

        Usa la caché si todavía es válida; si no, vuelve a leer de Google.
        """
        with self._candado:
            guardado = self._cache.get(pestana)
            if guardado is not None:
                momento, filas = guardado
                if time.monotonic() - momento < self.cache_segundos:
                    return filas

            filas = self._leer_de_google(pestana)
            self._cache[pestana] = (time.monotonic(), filas)
            return filas

    def _leer_de_google(self, pestana: str) -> list[dict]:
        hoja = self._abrir_hoja()
        valores = hoja.worksheet(pestana).get_all_values()
        if not valores:
            return []

        # Primera fila = encabezados. Se limpian espacios por si acaso.
        encabezados = [h.strip() for h in valores[0]]
        filas = []
        for fila in valores[1:]:
            # Google devuelve la cuadrícula completa; las filas vacías del
            # final no son registros.
            if not any(celda.strip() for celda in fila):
                continue
            # zip corta al más corto; si una fila viene más corta que los
            # encabezados, las celdas faltantes quedan como ''.
            fila = fila + [""] * (len(encabezados) - len(fila))
            filas.append(dict(zip(encabezados, fila)))
        return filas

    def vaciar_cache(self) -> None:
        """Obliga a releer de Google en la siguiente petición."""
        with self._candado:
            self._cache.clear()

    def refrescar(self, min_segundos: float = 10) -> bool:
        """Descarta las copias guardadas para que la siguiente lectura vaya a Google.

        Es lo que usa el botón "Actualizar" del dashboard. Las copias que se
        leyeron hace menos de `min_segundos` se conservan: así, aunque varios
        usuarios (o uno impaciente) pulsen el botón seguido, Google recibe a
        lo mucho una lectura cada `min_segundos` y no se agota la cuota.

        Regresa True si la siguiente petición va a leer de Google.
        """
        ahora = time.monotonic()
        with self._candado:
            vencidas = [p for p, (momento, _) in self._cache.items() if ahora - momento >= min_segundos]
            for pestana in vencidas:
                del self._cache[pestana]
            return bool(vencidas) or not self._cache
