# -*- coding: utf-8 -*-
"""Veta de la madera: la fibra corre a lo largo de cada pieza y las líneas se ven (antes eran de 2,4 mm y se perdían)."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import render_cpu as rc

from PySide6.QtWidgets import QApplication


def _tris(forma):
    return geo.teselar(forma)[0]


def test_las_coordenadas_de_veta_centran_la_pieza_y_ponen_su_lado_largo_en_y():
    q = rc.coordenadas_veta(_tris(geo.caja(18, 355, 1360, origen=(100, 50, 20))))
    assert np.ptp(q, axis=0) == pytest.approx([18, 1360, 355])           # el alto (el lado más largo) pasa a Y
    assert q.min(0) + q.max(0) == pytest.approx([0, 0, 0])


def test_una_parte_usa_el_marco_de_todo_el_cuerpo_y_sin_vertices_no_falla():
    cuerpo = _tris(geo.caja(100, 20, 20))
    q = rc.coordenadas_veta(cuerpo[:6], cuerpo)                         # dos triángulos de una cara
    assert np.abs(q[:, 1]).max() <= 50 + 1e-6 and np.abs(q[:, [0, 2]]).max() <= 10 + 1e-6
    assert rc.coordenadas_veta(np.zeros((0, 3))).shape == (0, 3)


def test_la_veta_cambia_a_lo_ancho_y_corre_a_lo_largo_con_lineas_visibles():
    rng = np.random.default_rng(1)
    c1, c2 = np.array([1.0, 1, 1]), np.zeros(3)
    P = np.c_[rng.uniform(-9, 9, 3000), rng.uniform(-600, 600, 3000), rng.uniform(-170, 170, 3000)]

    def gradiente(eje):
        paso = np.eye(3)[eje] * 0.5
        return np.abs(rc.veta_madera(P + paso, c1, c2)[:, 0] - rc.veta_madera(P - paso, c1, c2)[:, 0]).mean()

    assert gradiente(2) > 3 * gradiente(1)                              # a lo ancho cambia mucho más que a lo largo
    z = np.linspace(0, 100, 4001)
    t = rc.veta_madera(np.c_[np.zeros_like(z), np.zeros_like(z), z], c1, c2)[:, 0]
    lineas = int(((t[1:-1] < t[:-2]) & (t[1:-1] < t[2:]) & (t[1:-1] < 0.8)).sum())
    assert 8 <= lineas <= 25                                            # unas 15 líneas por 100 mm, no un borrón


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


def test_el_lienzo_da_coordenadas_de_veta_solo_a_la_madera(app_qt):
    from omnicad.ui.render import VentanaRender
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 18, "width": 355, "height": 1360, "name": "Lateral"})["ok"]
    assert api.llamar(s, "create_box", {"length": 50, "width": 50, "height": 50, "x": 300, "name": "Taco"})["ok"]
    assert api.llamar(s, "set_appearance", {"bodies": ["Lateral"], "appearance": "Madera - Roble"})["ok"]
    assert api.llamar(s, "set_appearance", {"bodies": ["Taco"], "appearance": "Pintura - Mate (Negro)"})["ok"]
    v = VentanaRender(s.doc)
    try:
        mallas = {m["id"]: m for m in v.lienzo._mallas}
        madera, pintura = (mallas[c.id] for c in s.doc.estado_final.cuerpos.values())
        assert madera["loc"].dtype == np.float32 and np.ptp(madera["loc"], axis=0) == pytest.approx([18, 1360, 355], abs=1e-3)
        assert pintura["loc"] is not None and np.array_equal(pintura["loc"], pintura["v"])      # sin madera, no se toca
    finally:
        s.doc.modificado = False
        v.close()
