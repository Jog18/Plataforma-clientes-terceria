"""Reporte de inspección en Excel (.xlsx) con el formato de Jesús (2026-10-07).

Columnas, en orden:
    FECHA, HORA, TURNO, NUMERO DE PARTE, CANTIDAD INSPECCIONADA,
    DIA PRODUCCIÓN, SERIAL, <una columna por defecto del catálogo>,
    CANTIDAD DE PIEZAS INSPECCIONADAS, SCRAP, %SCRAP, TOTAL DE PIEZAS OK,
    COMENTARIOS
y al final una fila "Total".

FECHA y HORA son las reales de captura. DIA PRODUCCIÓN es la fecha en que se
produjo el lote inspeccionado (columna FECHA DE PRODUCCION de la hoja).
Los registros se eligen por el día del tablero (de 6:00 a 5:59).
Reglas HBPO: scrap = NOK, OK = inspeccionadas - NOK.
"""

from datetime import date, time
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Colores del formato (los de la hoja de Excel que usa el equipo).
AZUL = "5B9BD5"
AZUL_OSCURO = "2E75B6"
BLANCO = "FFFFFF"
AMARILLO = "FFFF00"
ROJO = "FF0000"
VERDE = "70AD47"
FRANJA = "DDEBF7"

# (título, color de fondo, color de letra, texto vertical, ancho)
COLS_INICIO = [
    ("FECHA", AZUL, BLANCO, False, 12),
    ("HORA", AZUL, BLANCO, False, 10),
    ("TURNO", AZUL, BLANCO, False, 8),
    ("NUMERO DE PARTE", AZUL, BLANCO, False, 18),
    ("CANTIDAD INSPECCIONADA", AZUL, BLANCO, False, 16),
    ("DIA PRODUCCIÓN", AZUL, BLANCO, False, 13),
    ("SERIAL", AZUL, BLANCO, False, 14),
]
COLS_FINAL = [
    ("CANTIDAD DE PIEZAS INSPECCIONADAS", AMARILLO, "000000", True, 7),
    ("SCRAP", ROJO, BLANCO, True, 7),
    ("%SCRAP", ROJO, BLANCO, True, 8),
    ("TOTAL DE PIEZAS OK", VERDE, BLANCO, True, 7),
    ("COMENTARIOS", AZUL_OSCURO, BLANCO, False, 40),
]

LINEA = Side(style="thin", color="A6A6A6")
BORDE = Border(left=LINEA, right=LINEA, top=LINEA, bottom=LINEA)


def filtrar(filas: list[dict], desde: str, hasta: str, turno: str = "",
            parte: str = "", defecto: str = "") -> list[dict]:
    """Mismo filtro que el diálogo del tablero.

    desde/hasta: días de producción 'YYYY-MM-DD' (inclusive).
    parte: texto contenido en el número de parte, sin importar mayúsculas.
    defecto: solo registros que tengan piezas con ese defecto.
    """
    parte = parte.strip().upper()
    defecto = defecto.strip().upper()
    salida = []
    for r in filas:
        if not desde <= r["dia_produccion"] <= hasta:
            continue
        if turno and r["turno"] != turno:
            continue
        if parte and parte not in r["parte"].upper():
            continue
        if defecto and not any(d["defecto"] == defecto and d["cantidad"] > 0 for d in r["defectos"]):
            continue
        salida.append(r)
    return salida


def _fecha(texto: str | None):
    """'2026-10-06' -> date; si la hoja no trae fecha de producción, vacío."""
    return date.fromisoformat(texto) if texto else None


def _hora(texto: str):
    """'08:21:42' -> time(8, 21, 42) para que Excel la trate como hora."""
    try:
        h, m, s = (int(p) for p in texto.split(":"))
        return time(h, m, s)
    except ValueError:
        return texto


def armar_libro(filas: list[dict], catalogo_defectos: list[str], titulo_hoja: str = "Inspeccion") -> bytes:
    """Regresa el archivo .xlsx (en bytes) con el formato del reporte."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo_hoja[:31]

    columnas = (COLS_INICIO
                + [(d, BLANCO, ROJO, True, 7) for d in catalogo_defectos]
                + COLS_FINAL)

    # Encabezado.
    for c, (nombre, fondo, letra, vertical, ancho) in enumerate(columnas, start=1):
        celda = hoja.cell(row=1, column=c, value=nombre)
        celda.fill = PatternFill("solid", fgColor=fondo)
        celda.font = Font(bold=True, color=letra, size=10)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True,
                                    text_rotation=90 if vertical else 0)
        celda.border = BORDE
        hoja.column_dimensions[get_column_letter(c)].width = ancho
    hoja.row_dimensions[1].height = 120

    n_def = len(catalogo_defectos)
    col_def = len(COLS_INICIO) + 1          # primera columna de defecto
    col_insp2 = col_def + n_def             # CANTIDAD DE PIEZAS INSPECCIONADAS
    col_pct = col_insp2 + 2                 # %SCRAP
    idx_def = {d: i for i, d in enumerate(catalogo_defectos)}

    tot_def = [0] * n_def
    tot_insp = tot_nok = tot_ok = 0
    for i, r in enumerate(filas):
        por_def = [0] * n_def
        for d in r["defectos"]:
            if d["defecto"] in idx_def:
                por_def[idx_def[d["defecto"]]] += d["cantidad"]
        insp, nok, ok = r["insp"], r["nok"], r["ok"]
        valores = [
            date.fromisoformat(r["fecha"]), _hora(r["hora"]), r["turno"], r["parte"], insp,
            _fecha(r["fecha_produccion"]), r["serial"],
            *por_def,
            insp, r["scrap"], (nok / insp) if insp else 0, ok, r["comentarios"],
        ]
        fila = i + 2
        franja = PatternFill("solid", fgColor=FRANJA) if i % 2 else None
        for c, v in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=c, value=v)
            celda.border = BORDE
            if franja:
                celda.fill = franja
            if c != len(columnas):
                celda.alignment = Alignment(horizontal="center")
        hoja.cell(row=fila, column=1).number_format = "d/m/yyyy"
        hoja.cell(row=fila, column=2).number_format = "hh:mm:ss"
        hoja.cell(row=fila, column=6).number_format = "d/m/yyyy"
        hoja.cell(row=fila, column=col_pct).number_format = "0.00%"

        tot_def = [a + b for a, b in zip(tot_def, por_def)]
        tot_insp += insp
        tot_nok += nok
        tot_ok += ok

    # Fila "Total".
    fila = len(filas) + 2
    totales = {1: "Total", 5: tot_insp}
    totales.update({col_def + j: v for j, v in enumerate(tot_def)})
    totales.update({col_insp2: tot_insp, col_insp2 + 1: tot_nok,
                    col_pct: (tot_nok / tot_insp) if tot_insp else 0, col_pct + 1: tot_ok})
    for c in range(1, len(columnas) + 1):
        celda = hoja.cell(row=fila, column=c, value=totales.get(c))
        celda.font = Font(bold=True)
        celda.border = BORDE
        celda.alignment = Alignment(horizontal="center")
    hoja.cell(row=fila, column=col_pct).number_format = "0.00%"

    # Flechas de filtro sobre los registros (sin la fila Total) y encabezado fijo.
    hoja.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{max(fila - 1, 1)}"
    hoja.freeze_panes = "A2"
    # Al imprimir: horizontal y todas las columnas en una hoja de ancho.
    hoja.page_setup.orientation = "landscape"
    hoja.page_setup.fitToWidth = 1
    hoja.page_setup.fitToHeight = 0
    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.print_title_rows = "1:1"

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
