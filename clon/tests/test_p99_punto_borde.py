# -*- coding: utf-8 -*-
"""P-99: cada clic que suma un perfil a Extruir rearmaba el asa de la conicidad teselando TODOS los perfiles elegidos
(17 en el llavero: ~20 ms por clic). `punto_borde` recuerda los puntos de cada forma."""
import numpy as np

from omnicad.nucleo import geometria as geo
from omnicad.ui import manipuladores as mp


def test_p99_punto_borde_no_vuelve_a_teselar_las_mismas_formas(monkeypatch):
    formas = [geo.caja(10, 10, 1), geo.caja(4, 4, 1, origen=(20, 0, 0))]
    centro, direccion = np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])
    teseladas, original = [], geo.teselar
    monkeypatch.setattr(geo, "teselar", lambda f, *a, **k: teseladas.append(f) or original(f, *a, **k))
    primero = mp.punto_borde(formas, centro, direccion)
    assert len(teseladas) == 2 and primero[0] == 24.0                      # el borde más lejano en +X
    assert np.array_equal(mp.punto_borde(formas, centro, direccion), primero) and len(teseladas) == 2
    otra = geo.caja(4, 4, 1, origen=(30, 0, 0))                             # una forma nueva sí se tesela
    assert mp.punto_borde([*formas, otra], centro, direccion)[0] == 34.0 and len(teseladas) == 3
