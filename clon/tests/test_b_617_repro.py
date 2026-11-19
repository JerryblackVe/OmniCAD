# -*- coding: utf-8 -*-
"""Reproducción de B-617: Concéntrica arco–arco deforma los arcos en vez de trasladarlos."""

import pytest

from omnicad.restricciones import Boceto, resolver


def test_b617_concentrica_arco_arco_no_cambia_el_radio():
    """Dos arcos sueltos + Concéntrica: como Fusion, el arco se mueve entero, sin estirarse."""
    b = Boceto()
    a1 = b.agregar_arco_centro((0, 0), (6, 0), (0, 6))
    a2 = b.agregar_arco_centro((30, 0), (36, 0), (30, 6))
    b.agregar_restriccion("concentrica", [a1, a2])
    assert resolver(b).ok
    assert b.coords(b.curvas[a1].centro) == pytest.approx(b.coords(b.curvas[a2].centro), abs=1e-6)
    assert (b.radio(a1), b.radio(a2)) == pytest.approx((6, 6), abs=1e-3)


def test_b617_arrastrar_el_centro_no_deforma_el_otro_arco():
    """Como el editor (`_mover_punto`): al arrastrar el centro, el arco entero lo acompaña y el otro no se estira."""
    b = Boceto()
    a1 = b.agregar_arco_centro((0, 0), (6, 0), (0, 6))
    a2 = b.agregar_arco_centro((30, 0), (36, 0), (30, 6))
    b.agregar_restriccion("concentrica", [a1, a2])
    previo = resolver(b)
    assert previo.ok
    centro = b.curvas[a1].centro
    cx, cy = b.coords(centro)
    b.puntos[centro].x, b.puntos[centro].y = cx + 4, cy + 3
    for q in (b.curvas[a1].inicio, b.curvas[a1].fin):
        b.puntos[q].x, b.puntos[q].y = b.puntos[q].x + 4, b.puntos[q].y + 3
    assert resolver(b, arrastrado=centro, previo=previo).ok
    assert (b.radio(a1), b.radio(a2)) == pytest.approx((6, 6), abs=1e-3)
