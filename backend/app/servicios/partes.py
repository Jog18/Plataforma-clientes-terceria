"""Estandarización de números de parte.

La app de captura registra el mismo número de parte de varias formas
(con o sin 'P', con espacios, escaneando la etiqueta completa…). Aquí se
llevan todas a una sola forma para que el dashboard las cuente juntas.

Reglas (definidas por Jesús, 2026-09-30), en este orden:
    1. Mayúsculas y sin ningún espacio.
    2. Si empieza con 'P', se quita.
    3. Si ahora empieza con 'MB' o 'MC', se le agrega '8' al inicio.
    4. Si contiene 'BCS' seguido de más texto, se corta justo después de 'BCS'.

Ejemplos:
    'P8MB863242K  BDE'                          -> '8MB863242KBDE'
    'PMB863242E Z85'                            -> '8MB863242EZ85'
    '8MB 863 242 K BCS-02S-1-17.07.26-0239372'  -> '8MB863242KBCS'
"""

import re

# Casos que las reglas no alcanzan a corregir. Se agrega una línea por
# número mal capturado: 'como llega después de las reglas' -> 'como debe quedar'.
CORRECCIONES: dict[str, str] = {
    # "8MB863242KBDX": "8MB863242KBDE",
}

PREFIJOS_SIN_8 = ("MB", "MC")
SUFIJO_CORTE = "BCS"


def estandarizar_parte(texto: str) -> str:
    # 1. Mayúsculas y sin espacios (incluye tabuladores y dobles espacios).
    parte = re.sub(r"\s+", "", texto or "").upper()

    # 2. Quitar la 'P' inicial.
    if parte.startswith("P"):
        parte = parte[1:]

    # 3. Agregar el '8' que faltó al capturar.
    if parte.startswith(PREFIJOS_SIN_8):
        parte = "8" + parte

    # 4. Cortar lo que venga después de 'BCS' (etiqueta escaneada completa).
    posicion = parte.find(SUFIJO_CORTE)
    if posicion != -1:
        parte = parte[: posicion + len(SUFIJO_CORTE)]

    # Excepciones puntuales que las reglas no cubren.
    return CORRECCIONES.get(parte, parte)
