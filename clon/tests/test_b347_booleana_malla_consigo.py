# -*- coding: utf-8 -*-
"""B-347 (caza, tema boolean): boolean_operation con una malla devolvía INTERNAL_ERROR (TypeError en
geometria._explorar) en vez del error de siempre «el objetivo no puede ser también herramienta»."""
import pytest

from omnicad import api


@pytest.mark.parametrize("malla", [False, True])
def test_el_objetivo_no_puede_ser_herramienta(malla):
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 40})
    cuerpo = "op1.c1"
    if malla:
        assert api.llamar(s, "tessellate", {"bodies": "Cuerpo1"})["ok"]
        cuerpo = "op2.c1"
    r = api.llamar(s, "boolean_operation", {"target": cuerpo, "tools": [cuerpo]})
    assert not r["ok"] and r["error_kind"] != "INTERNAL_ERROR" and "también herramienta" in r["mensaje"]


@pytest.mark.parametrize("operacion", ["join", "cut", "intersect"])
def test_combinar_con_una_malla_pide_combinar_mallas(operacion):
    """Gemelo: dos mallas distintas (o malla y sólido) también daban TypeError; como Fusion, van a Combinar mallas."""
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 40})
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": 100})
    assert api.llamar(s, "tessellate", {"bodies": "Cuerpo2"})["ok"]
    r = api.llamar(s, "boolean_operation", {"target": "op1.c1", "tools": ["op3.c1"], "operation": operacion})
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED" and "combine_meshes" in r["mensaje"]
