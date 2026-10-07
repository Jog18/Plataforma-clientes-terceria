"""Limpieza de registros: horas y orden."""

import pytest

from datetime import date

from app.servicios.inspeccion import construir_paquete, dia_produccion, normalizar_hora


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


@pytest.mark.parametrize("hora, esperado", [
    ("21:30:00", date(2026, 10, 5)),   # empieza el 3er turno del lunes 5
    ("23:59:59", date(2026, 10, 5)),
    ("00:00:00", date(2026, 10, 4)),   # capturado ya el martes...
    ("05:59:59", date(2026, 10, 4)),   # ...cuenta para el día anterior
    ("06:00:00", date(2026, 10, 5)),   # a las 6:00 empieza el día nuevo
    ("", date(2026, 10, 5)),
    ("mediodía", date(2026, 10, 5)),
])
def test_dia_produccion_cierra_a_las_6(hora, esperado):
    assert dia_produccion(date(2026, 10, 5), hora) == esperado


def test_el_tercer_turno_queda_en_el_dia_en_que_empezo():
    filas = [
        {"ID": "a", "FECHA": "5/10/2026", "TURNO": "3ro", "HORA": "22:10:00", "PIEZAS INSP.": "5"},
        {"ID": "b", "FECHA": "6/10/2026", "TURNO": "3ro", "HORA": "2:30:00", "PIEZAS INSP.": "5"},
        {"ID": "c", "FECHA": "6/10/2026", "TURNO": "1ro", "HORA": "6:05:00", "PIEZAS INSP.": "5"},
        {"ID": "d", "FECHA": "1/10/2026", "TURNO": "3ro", "HORA": "3:00:00", "PIEZAS INSP.": "5"},
    ]
    por_id = {r["id"]: r for r in construir_paquete(filas, [])["filas"]}
    assert por_id["a"]["dia_produccion"] == "2026-10-05"
    assert por_id["b"]["dia_produccion"] == "2026-10-05"
    assert por_id["b"]["fecha"] == "2026-10-06"          # la fecha real no se toca
    assert por_id["c"]["dia_produccion"] == "2026-10-06"
    assert por_id["d"]["dia_produccion"] == "2026-09-30"  # cambio de mes
