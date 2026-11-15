# -*- coding: utf-8 -*-
"""B-527: el parche de un perfil con hueco (anillo r5–r15) daba el disco lleno (706,9) e ignoraba el hueco."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _anillo():
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"plane": "XY", "name": "S"})["ok"]
    assert api.llamar(s, "draw_circle", {"radius": 15})["ok"] and api.llamar(s, "draw_circle", {"radius": 5})["ok"]
    return s


@pytest.mark.parametrize("perfil, area", [(1, math.pi * (15 ** 2 - 5 ** 2)), (0, math.pi * 5 ** 2)])
def test_el_parche_respeta_el_hueco_del_perfil(perfil, area):
    s = _anillo()
    assert api.llamar(s, "create_patch", {"boundary": {"sketch": "S", "profile": perfil}})["ok"]
    (cuerpo,) = s.doc.estado_final.cuerpos.values()
    assert geo.area(cuerpo.forma) == pytest.approx(area, rel=1e-6) and geo.es_valida(cuerpo.forma)
