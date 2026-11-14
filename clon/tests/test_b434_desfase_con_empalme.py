# -*- coding: utf-8 -*-
"""B-434: Pulsar/tirar (desfase de cara) de la cara de arriba de una caja con un empalme en el borde arrastraba la cadena
tangente hasta la pared lateral y la caja crecía de costado (40×30×20 con un empalme de 5, +5 mm → 40×35×25 y
34141,59 mm³). Fusion solo sube la cara: el empalme conserva el radio y la pared se estira (40×30×25)."""
import math

import pytest

from omnicad import api

PERDIDA = (1 - math.pi / 4) * 25 * 40          # lo que quita un empalme de 5 en una arista de 40


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.mark.parametrize("aristas, empalmes", [(None, 0), (">Z and |X and <Y", 1),
                                                ([">Z and |X and <Y", ">Z and |X and >Y"], 2)])
@pytest.mark.parametrize("distancia", [5, -5])
def test_desfase_de_la_cara_de_arriba_solo_mueve_la_cara(aristas, empalmes, distancia):
    s = api.Sesion()
    _ok(s, "create_box", length=40, width=30, height=20)
    if aristas:
        _ok(s, "fillet", edges=aristas, radius=5)
    arriba = next(c["id"] for c in _ok(s, "find_faces", body="Cuerpo1")["faces"]
                  if c["type"] == "plane" and c["normal"][2] > 0.999)
    _ok(s, "offset_faces", faces=[arriba], distance=distancia)
    g = _ok(s, "check_geometry", body="Cuerpo1")["bodies"][0]
    assert g["valid"] and g["closed"] and g["faces"] == 6 + empalmes     # el empalme sigue siendo una sola cara
    assert g["bounding_box"]["size"] == pytest.approx([40, 30, 20 + distancia])
    assert g["volume"] == pytest.approx(40 * 30 * (20 + distancia) - empalmes * PERDIDA, rel=1e-6)
