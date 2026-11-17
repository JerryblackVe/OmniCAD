# -*- coding: utf-8 -*-
"""Reproducción de B-617: Concéntrica arco–arco deforma los arcos en vez de trasladarlos."""

import pytest

from omnicad.restricciones import Boceto, resolver


@pytest.mark.xfail(strict=True, reason="B-617")
def test_b617_concentrica_arco_arco_no_cambia_el_radio():
    """Dos arcos sueltos + Concéntrica: como Fusion, el arco se mueve entero, sin estirarse."""
    b = Boceto()
    a1 = b.agregar_arco_centro((0, 0), (6, 0), (0, 6))
    a2 = b.agregar_arco_centro((30, 0), (36, 0), (30, 6))
    b.agregar_restriccion("concentrica", [a1, a2])
    assert resolver(b).ok
    assert b.coords(b.curvas[a1].centro) == pytest.approx(b.coords(b.curvas[a2].centro), abs=1e-6)
    assert (b.radio(a1), b.radio(a2)) == pytest.approx((6, 6), abs=1e-3)
