"""Limpieza de registros: horas y orden."""

import pytest

from app.servicios.inspeccion import construir_paquete, normalizar_hora


@pytest.mark.parametrize("crudo, esperado", [
    ("8:21:42", "08:21:42"),
    ("13:03:05", "13:03:05"),
    ("9:05", "09:05:00"),
    ("  8:21:42 ", "08:21:42"),
    ("", ""),
    ("mediodía", "mediodía"),
])
def test_normalizar_hora(crudo, esperado):
    assert normalizar_hora(crudo) == esperado


def fila(i, hora):
    return {"ID": f"id{i}", "FECHA": "2/10/2026", "TURNO": "1ro", "HORA": hora,
            "NUMERO DE PARTE": "P8MB863242K BDE", "PIEZAS INSP.": "14", "PIEZAS NOK": "0"}


def test_el_ultimo_registro_del_dia_es_el_de_la_tarde():
    # Horas reales de la hoja del 2/10/2026: sin cero a la izquierda.
    horas = ["8:21:18", "8:21:42", "10:06:50", "13:03:05", "13:03:42"]
    paquete = construir_paquete([fila(i, h) for i, h in enumerate(horas)], [])
    assert [r["hora"] for r in paquete["filas"]] == [
        "08:21:18", "08:21:42", "10:06:50", "13:03:05", "13:03:42"]
    # Y como texto, el último en orden alfabético ya es también el último en el tiempo.
    assert max(r["fecha"] + " " + r["hora"] for r in paquete["filas"]).endswith("13:03:42")
