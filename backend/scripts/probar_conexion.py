"""Prueba de conexión a Google Sheets con la cuenta de servicio (el "robot").

Se conecta como el robot, abre la hoja por su ID y muestra, por cada pestaña,
los encabezados y las primeras filas. Si ves tus datos, la Fase 1 quedó lista.

Uso (desde la carpeta raíz del proyecto):
    pip install -r requirements.txt
    python backend/scripts/probar_conexion.py
"""

import sys
from pathlib import Path

import gspread
from google.auth.exceptions import RefreshError

# El ID no es secreto: sin el acceso del robot no sirve de nada.
SHEET_ID = "1Bmzr7_F1GXc7204Jtu8rtUkE7RaxsGFsjGSPDR-f-GA"

# La llave JSON del robot. Vive solo en tu computadora (está en .gitignore).
CREDENCIALES = Path(__file__).resolve().parents[1] / "credenciales.json"

FILAS_DE_MUESTRA = 3


def main():
    if not CREDENCIALES.exists():
        sys.exit(
            f"No encontré la llave en {CREDENCIALES}.\n"
            "Copia el JSON que descargaste de Google Cloud a esa ruta "
            "y renómbralo a credenciales.json."
        )

    # gspread se autentica directo con la llave; ya no hace falta oauth2client.
    cliente = gspread.service_account(filename=CREDENCIALES)
    print(f"Conectado como: {cliente.http_client.auth.service_account_email}\n")

    try:
        hoja = cliente.open_by_key(SHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        sys.exit(
            "Google no deja al robot ver la hoja.\n"
            "Revisa en 'Compartir' que el correo de arriba tenga rol de Lector."
        )
    except RefreshError:
        sys.exit(
            "Google rechazó la llave. Puede estar borrada o ser de otra cuenta.\n"
            "Genera una nueva en Google Cloud (Cuenta de servicio > Claves)."
        )
    except gspread.exceptions.APIError as error:
        sys.exit(
            f"Google respondió con un error: {error}\n"
            "Si menciona 'has not been used' o 'disabled', habilita la "
            "Google Sheets API en el proyecto de Google Cloud."
        )

    print(f"Documento: {hoja.title}")
    for pestana in hoja.worksheets():
        # Filas 1 a 4: encabezados + filas de muestra.
        filas = pestana.get_values(f"1:{FILAS_DE_MUESTRA + 1}")
        print(f"\n=== Pestaña: {pestana.title} "
              f"({pestana.row_count} filas x {pestana.col_count} columnas) ===")
        if not filas:
            print("(vacía)")
            continue
        print("Encabezados:", filas[0])
        for fila in filas[1:]:
            print("  ", fila)


if __name__ == "__main__":
    main()
