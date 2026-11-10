# -*- coding: utf-8 -*-
"""P-123: las curvas de un boceto terminado se muestrean una vez. Cada redibujo del visor (un clic en Aspecto, aceptar un
comando) volvía a muestrear todas las splines: ~65 ms por boceto con el texto de un SVG (377 splines)."""
import numpy as np
import pytest

from omnicad import api
from omnicad.ui import visor3d


@pytest.fixture
def boceto():
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"plane": "XY"})["ok"]
    assert api.llamar(s, "draw_spline", {"points": [[0, 0], [10, 5], [20, -5], [30, 0]]})["ok"]
    assert api.llamar(s, "draw_circle", {"radius": 4, "center_x": 50})["ok"]
    return s.doc.estado_final.bocetos[s.doc.operaciones[-1].id]


@pytest.fixture
def muestreos(monkeypatch):
    cuenta = []
    original = visor3d.muestrear_primitiva
    monkeypatch.setattr(visor3d, "muestrear_primitiva", lambda prim: (cuenta.append(prim[0]), original(prim))[1])
    return cuenta


def test_el_segundo_redibujo_no_vuelve_a_muestrear(boceto, muestreos):
    primera = visor3d.polilineas_boceto(boceto)
    n = len(muestreos)
    assert n >= 2 and len(primera) == 2
    segunda = visor3d.polilineas_boceto(boceto)
    assert len(muestreos) == n
    assert all(np.array_equal(a, b) for a, b in zip(primera, segunda, strict=True))


def test_una_curva_nueva_se_dibuja(boceto, muestreos):
    antes = visor3d.polilineas_boceto(boceto)
    boceto.boceto.agregar_linea((0, 20), (30, 20))         # el boceto cambió en el lugar
    despues = visor3d.polilineas_boceto(boceto)
    assert len(despues) == len(antes) + 1
    assert any(np.allclose(p[[0, -1], 1], 20) for p in despues)
