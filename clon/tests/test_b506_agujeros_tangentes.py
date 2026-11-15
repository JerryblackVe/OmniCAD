# -*- coding: utf-8 -*-
"""B-506: dos agujeros del mismo paso que se tocan justo en el borde daban «ok» con un cuerpo que se cruza consigo
mismo (check_geometry: valid=False), también al llegar por set_parameter. Ahora es un error de un renglón."""
import time

import pytest

from omnicad import api
from omnicad.nucleo import solidos_crear as sc


def _sesion(**agujero):
    s = api.Sesion()
    assert api.llamar(s, "create_parameter", {"name": "d", "expression": "6 mm"})["ok"]
    assert api.llamar(s, "create_box", {"length": 80, "width": 40, "height": 10})["ok"]
    assert api.llamar(s, "create_hole", dict(face=">Z", through_all=True, **agujero))["ok"]
    return s


def _sano(s):
    (cuerpo,) = api.llamar(s, "check_geometry", {})["result"]["bodies"]
    return cuerpo["valid"] and cuerpo["self_intersections"] == 0


@pytest.mark.parametrize("agujero, tangente", [
    ({"diameter": "d", "points": [[-4, 0], [4, 0]]}, 8),                                  # Ø tangentes entre sí
    ({"diameter": 4, "points": [[-10, 0], [10, 0]], "hole_type": "counterbore",           # abocardados tangentes
      "counterbore_diameter": "d", "counterbore_depth": 3}, 20),
])
def test_agujeros_del_mismo_paso_que_se_tocan_justo_son_un_error(agujero, tangente):
    s = _sesion(**agujero)
    for v in (tangente - 0.01, tangente + 0.01):                                          # al lado: válidos
        assert api.llamar(s, "set_parameter", {"name": "d", "expression": f"{v} mm"})["ok"] and _sano(s)
    r = api.llamar(s, "set_parameter", {"name": "d", "expression": f"{tangente} mm"})
    assert not r["ok"] and r["mensaje"].endswith("Dos agujeros se tocan justo: espesor cero."), r
    assert _sano(s)                                                                       # quedó como estaba


@pytest.mark.parametrize("agujero, mensaje", [
    ({"diameter": 8, "points": [[-4, 0], [4, 0]]}, "Dos agujeros se tocan justo: espesor cero."),
    ({"diameter": 10, "points": [[0, 15]]}, "El agujero toca justo una pared: espesor cero."),   # B-165, regla 14
])
def test_creado_directo_da_el_error_en_un_renglon(agujero, mensaje):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 80, "width": 40, "height": 10})["ok"]
    r = api.llamar(s, "create_hole", dict(face=">Z", through_all=True, **agujero))
    assert not r["ok"] and r["mensaje"].endswith(mensaje) and len(mensaje) <= 50, r


def test_doscientos_agujeros_separados_no_se_miden_entre_si():
    herramientas = [sc.herramienta_agujero((x, y, 0), (0, 0, -1), profundidad=10, diametro=2)
                    for x in range(-38, 39, 4) for y in range(-18, 19, 4)]
    t = time.perf_counter()
    sc.exigir_agujeros_separados(herramientas)
    assert len(herramientas) == 200 and time.perf_counter() - t < 0.5
