# -*- coding: utf-8 -*-
"""Preparación: cobertura de restricciones del boceto aún sin test (combinaciones nuevas)."""
import math

import pytest

from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.solver import resolver

TOL = 1e-6


def _reflejo(px, py, ax, ay, ux, uy):
    t = (px - ax) * ux + (py - ay) * uy
    fx, fy = ax + t * ux, ay + t * uy
    return 2 * fx - px, 2 * fy - py


def test_coincidente_punto_arco():
    b = Boceto()
    k = b.agregar_arco_centro((60, 40), (72, 40), (60, 52))
    q = b.agregar_punto(80, 45)
    b.agregar_restriccion("coincidente", [q, k])
    r = resolver(b, {})
    assert r.ok
    cx, cy = b.coords(b.curvas[k].centro)
    assert math.dist(b.coords(q), (cx, cy)) == pytest.approx(b.radio(k), abs=TOL)
    copia = Boceto.desde_dict(b.a_dict())
    assert resolver(copia, {}).ok
    cx2, cy2 = copia.coords(copia.curvas[k].centro)
    assert math.dist(copia.coords(q), (cx2, cy2)) == pytest.approx(copia.radio(k), abs=TOL)


def test_igual_arco_circulo():
    b = Boceto()
    k1 = b.agregar_arco_centro((40, 40), (50, 40), (40, 50))
    k2 = b.agregar_circulo((90, 40), 15)
    b.agregar_restriccion("igual", [k1, k2])
    r = resolver(b, {})
    assert r.ok
    assert b.radio(k1) == pytest.approx(b.radio(k2), abs=TOL)
    copia = Boceto.desde_dict(b.a_dict())
    assert resolver(copia, {}).ok
    assert copia.radio(k1) == pytest.approx(copia.radio(k2), abs=TOL)


def test_simetria_arco_arco():
    b = Boceto()
    eje = b.agregar_linea((60, 20), (60, 90))
    k1 = b.agregar_arco_centro((40, 40), (50, 40), (40, 50))
    k2 = b.agregar_arco_centro((80, 40), (70, 40), (80, 50))
    b.agregar_restriccion("simetrica", [k1, k2, eje])
    r = resolver(b, {})
    assert r.ok
    a, c = b.coords(b.curvas[eje].p1), b.coords(b.curvas[eje].p2)
    ux, uy = (c[0] - a[0], c[1] - a[1])
    n = math.hypot(ux, uy) or 1.0
    ux, uy = ux / n, uy / n
    (cx1, cy1), (cx2, cy2) = b.coords(b.curvas[k1].centro), b.coords(b.curvas[k2].centro)
    rx, ry = _reflejo(cx1, cy1, a[0], a[1], ux, uy)
    assert (rx, ry) == pytest.approx((cx2, cy2), abs=TOL)
    assert b.radio(k1) == pytest.approx(b.radio(k2), abs=TOL)


def test_simetria_circulo_arco():
    b = Boceto()
    eje = b.agregar_linea((60, 20), (60, 90))
    k1 = b.agregar_circulo((40, 50), 9)
    k2 = b.agregar_arco_centro((80, 50), (90, 50), (80, 60))
    b.agregar_restriccion("simetrica", [k1, k2, eje])
    r = resolver(b, {})
    assert r.ok
    a, c = b.coords(b.curvas[eje].p1), b.coords(b.curvas[eje].p2)
    ux, uy = (c[0] - a[0], c[1] - a[1])
    n = math.hypot(ux, uy) or 1.0
    ux, uy = ux / n, uy / n
    (cx1, cy1), (cx2, cy2) = b.coords(b.curvas[k1].centro), b.coords(b.curvas[k2].centro)
    rx, ry = _reflejo(cx1, cy1, a[0], a[1], ux, uy)
    assert (rx, ry) == pytest.approx((cx2, cy2), abs=TOL)
    assert b.radio(k1) == pytest.approx(b.radio(k2), abs=TOL)


def test_tangente_circulo_arco():
    b = Boceto()
    k1 = b.agregar_circulo((50, 40), 10)
    k2 = b.agregar_arco_centro((75, 40), (83, 40), (75, 48))
    b.agregar_restriccion("tangente", [k1, k2])
    r = resolver(b, {})
    assert r.ok
    c1 = b.coords(b.curvas[k1].centro)
    c2 = b.coords(b.curvas[k2].centro)
    assert math.dist(c1, c2) == pytest.approx(b.radio(k1) + b.radio(k2), abs=TOL)
