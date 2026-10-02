"""Botón "Actualizar": lectura forzada de la hoja con límite mínimo entre lecturas."""

from pathlib import Path

from app.fuentes.gsheets import FuenteGoogleSheets


class FuenteContada(FuenteGoogleSheets):
    """Cuenta cuántas veces se va a Google, sin conectarse a nada."""

    def __init__(self):
        super().__init__("id", Path("no-existe.json"), cache_segundos=300)
        self.lecturas = 0

    def _leer_de_google(self, pestana):
        self.lecturas += 1
        return [{"pestana": pestana}]


def test_sin_refrescar_usa_la_copia():
    f = FuenteContada()
    f.leer_tabla("A")
    f.leer_tabla("A")
    assert f.lecturas == 1


def test_refrescar_obliga_a_releer():
    f = FuenteContada()
    f.leer_tabla("A")
    assert f.refrescar(min_segundos=0) is True
    f.leer_tabla("A")
    assert f.lecturas == 2


def test_refrescar_respeta_el_minimo_entre_lecturas():
    f = FuenteContada()
    f.leer_tabla("A")
    assert f.refrescar(min_segundos=60) is False
    f.leer_tabla("A")
    assert f.lecturas == 1


def test_refrescar_con_cache_vacia_dice_que_leera():
    assert FuenteContada().refrescar() is True


def test_ruta_datos_llama_a_refrescar_solo_si_se_pide():
    from fastapi.testclient import TestClient
    from app.clientes import CLIENTES
    from app.dependencias import obtener_cliente, obtener_fuente
    from app.main import app

    llamadas = []

    class Falsa:
        def refrescar(self, minimo):
            llamadas.append(minimo)

        def leer_tabla(self, pestana):
            return []

    app.dependency_overrides[obtener_fuente] = lambda: Falsa()
    app.dependency_overrides[obtener_cliente] = lambda: next(iter(CLIENTES.values()))
    try:
        with TestClient(app) as c:
            assert c.get("/api/datos").status_code == 200
            assert llamadas == []
            assert c.get("/api/datos?refrescar=1").status_code == 200
            assert len(llamadas) == 1
    finally:
        app.dependency_overrides.clear()
