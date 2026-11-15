# -*- coding: utf-8 -*-
"""B-334: Desfase de caras sobre una cara con hoyuelos (patrón de esferas) dejaba el cuerpo abierto y salía ok."""
import pytest

from omnicad import api


def _llamar(sesion, nombre, **argumentos):
    r = api.llamar(sesion, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


@pytest.mark.parametrize("distancia", [10.0, -5.0, 1e6])
def test_el_cuerpo_queda_cerrado(distancia):
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="YZ")
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=60, y2=40)
    _llamar(s, "extrude", sketch="Boceto1", profile="all", distance=20)
    _llamar(s, "create_geometric_pattern", body="op2.c1", faces=["Cuerpo1/F5"], distance=22.0, target="op2.c1")
    _llamar(s, "offset_faces", body="op2.c1", faces=["Cuerpo1/F4"], distance=distancia)
    revision = _llamar(s, "check_geometry", body="op2.c1")["bodies"][0]
    assert revision["closed"] and revision["free_edges"] == 0
    assert revision["volume"] == pytest.approx(48000 + 60 * 40 * distancia, rel=1e-2)    # menos los hoyuelos y sus pozos (0,2–0,8 %)


def test_b525_desfase_que_aplasta_el_hueco_da_error_y_no_deja_cruces():
    """B-525: subir 17 mm el piso de una caja vaciada a 3 mm (llega al borde) daba «ok» con 4 autointersecciones."""
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=50, height=20)
    _llamar(s, "shell", body="Cuerpo1", thickness=3, faces=">Z")
    caras = ["Cuerpo1/F2", "Cuerpo1/F9", "Cuerpo1/F11"]
    r = api.llamar(s, "offset_faces", {"body": "op1.c1", "faces": caras, "distance": 17.0})
    assert not r["ok"] and "se chocan" in r["mensaje"], r
    _llamar(s, "offset_faces", body="op1.c1", faces=caras, distance=5.0)     # con lugar, sigue andando
    revision = _llamar(s, "check_geometry", body="op1.c1")["bodies"][0]
    assert revision["closed"] and revision["volume"] > 14568
