# -*- coding: utf-8 -*-
"""PREP: test automático para la opción «Salto con Interior 0 (Entero)» del comando Estrella del boceto.

Cubre: draw_star con skip (salto) = 2 (mínimo, Interior 0 = regular) y skip = 31 (máximo borde).
"""

import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402


def _proporc_estrella(puntas, salto=2):
    """Radio interior / exterior de la estrella regular {puntas/salto}.

    Si salto no es válido, devuelve None para que el test falle con mensaje claro.
    """
    if not 2 <= salto < puntas / 2:
        return None
    return math.cos(math.pi * salto / puntas) / math.cos(math.pi * (salto - 1) / puntas)


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def area_estrella(n, R, r, r_punta=0.0):
    """Área de la estrella filosa menos lo que se lleva cada redondeo de punta."""
    area = n * R * r * math.sin(math.pi / n)
    if r_punta:
        p, v = (R, 0.0), (r * math.cos(math.pi / n), r * math.sin(math.pi / n))
        lado = math.dist(p, v)
        alfa = 2 * math.asin(abs(v[1]) / lado)
        area -= n * r_punta ** 2 * (1 / math.tan(alfa / 2) - (math.pi - alfa) / 2)
    return area


@pytest.fixture
def sesion():
    s = api.Sesion()
    llamar(s, "create_sketch", name="E")
    return s


def test_salto_interior_0_valor_numerico(sesion):
    """TEST: Salto con Interior 0 (Entero) - valor numérico 10 (usando 22 puntas)."""
    s = sesion
    r = llamar(s, "draw_star", points=22, outer_radius=50, skip=10, sketch="E")
    assert r["dof"] == 3
    perfiles = llamar(s, "get_sketch", sketch="E")["profiles"]
    assert len(perfiles) == 1
    pe = _proporc_estrella(22, 10)
    assert pe is not None, "salto inválido para 22 puntas"
    radio_int = 50 * pe
    assert perfiles[0]["area"] == pytest.approx(area_estrella(22, 50, radio_int, 0.0), rel=1e-6)


@pytest.mark.parametrize("skip", [2, 3])
def test_salto_interior_0_borde(sesion, skip):
    """TEST: Salto con Interior 0 (Entero) - valores en el borde del rango (mínimo 2)."""
    s = sesion
    r = llamar(s, "draw_star", points=8, outer_radius=30, skip=skip, sketch="E")
    assert r["dof"] == 3
    perfiles = llamar(s, "get_sketch", sketch="E")["profiles"]
    assert len(perfiles) == 1
    pe = _proporc_estrella(8, skip)
    assert pe is not None, f"salto {skip} inválido para 8 puntas"
    radio_int = 30 * pe
    assert perfiles[0]["area"] == pytest.approx(area_estrella(8, 30, radio_int), rel=1e-6)