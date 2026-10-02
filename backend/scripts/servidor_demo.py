"""Servidor de demostración con datos inventados.

Sirve para ver el dashboard sin la llave de Google: reemplaza la fuente de
datos por filas generadas al azar con la misma forma que la hoja real.
No se usa en producción.

Uso (desde la raíz del proyecto):
    python backend/scripts/servidor_demo.py          # usuario demo / demo-demo-demo-1
"""

import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seguridad.contrasenas import generar_hash  # noqa: E402

os.environ.setdefault("ENTORNO", "desarrollo")
os.environ.setdefault("ADMIN_USUARIO", "demo")
os.environ.setdefault("ADMIN_HASH", generar_hash("demo-demo-demo-1"))

import uvicorn  # noqa: E402

from app import dependencias  # noqa: E402
from app.main import app  # noqa: E402

DEFECTOS = ["RAYONES", "GOLPES/DAÑOS", "REBABAS", "MANCHAS", "CRAKEO", "SUCIEDAD", "AJUSTE"]
PARTES = ["8MB863242KBDE", "8MB863242FBCS", "8MC863242GITC", "8MB863969AVS8", "8MB867242JITB", "1100961"]
TURNOS = ["1ro", "2do", "3ro"]


def filas_demo(dias: int = 70, semilla: int = 7) -> tuple[list[dict], list[dict]]:
    azar = random.Random(semilla)
    insp, defs = [], []
    n = 0
    for d in range(dias):
        fecha = date.today() - timedelta(days=dias - d)
        for turno in TURNOS:
            for _ in range(azar.randint(2, 6)):
                n += 1
                pzs = azar.randint(20, 120)
                nok = min(pzs, max(0, int(azar.gauss(pzs * 0.04, pzs * 0.03))))
                ident = f"{n:08x}"
                insp.append({
                    "ID": ident, "FECHA": fecha.strftime("%d/%m/%Y"), "TURNO": turno,
                    "HORA": f"{azar.randint(6, 22)}:{azar.randint(0, 59):02d}:00",
                    "NUMERO DE PARTE": azar.choice(PARTES), "SERIAL": f"S{azar.randint(100000, 999999)}",
                    "FECHA DE PRODUCCION": (fecha - timedelta(days=1)).strftime("%d/%m/%Y"),
                    "PIEZAS INSP.": str(pzs), "PIEZAS NOK": str(nok), "PIEZAS OK": str(pzs - nok),
                    "DEFECTO": "", "SCRAP": str(nok),
                    "COMENTARIOS": azar.choice(["", "", "Lote con <etiqueta> rara", "Revisar empaque", "OK"]),
                })
                restante = nok
                while restante > 0:
                    c = azar.randint(1, restante)
                    defs.append({"ID DEFECTO": str(len(defs) + 1), "ID INSPECCION": ident,
                                 "DEFECTO": azar.choice(DEFECTOS), "CANTIDAD": str(c), "TEXTO": ""})
                    restante -= c
    return insp, defs


class FuenteDemo:
    def __init__(self):
        self.insp, self.defs = filas_demo()

    def leer_tabla(self, pestana: str) -> list[dict]:
        return self.defs if "Defectos" in pestana else self.insp

    def refrescar(self, min_segundos: float = 10) -> bool:
        return True  # los datos de demo no vienen de ninguna parte


app.dependency_overrides[dependencias.obtener_fuente] = lambda: FuenteDemo()

if __name__ == "__main__":
    puerto = int(os.environ.get("PUERTO", "8000"))
    print(f"Demo en http://127.0.0.1:{puerto}  (usuario: demo, contraseña: demo-demo-demo-1)")
    uvicorn.run(app, host="127.0.0.1", port=puerto)
