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
