# -*- coding: utf-8 -*-
"""B-394: Engrosar de caras cuyo sólido probá menos espesor da error claro; el caso sano sigue andando."""
from omnicad import api


def _caja_abierta():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 50, "height": 20})["ok"]
    assert api.llamar(s, "shell", {"body": "Cuerpo1", "faces": ">Z"})["ok"]
    return s


def test_engrosar_borde_y_dos_paredes_de_caja_abierta_da_error_claro_y_deja_el_documento():
    s = _caja_abierta()
    r = api.llamar(s, "thicken", {"faces": ["Cuerpo1/F6", "Cuerpo1/F4", "Cuerpo1/F9"]})
    assert not r["ok"] and "probá menos espesor" in r["mensaje"]
    assert len(api.llamar(s, "get_timeline", {})["result"]["steps"]) == 2             # caja y vaciado: sin paso nuevo


def test_engrosar_una_pared_de_la_misma_caja_sigue_dando_solido():
    s = _caja_abierta()
    r = api.llamar(s, "thicken", {"faces": ["Cuerpo1/F4"]})
    assert r["ok"], r
    assert r["result"]["bodies_created"][0]["volume"] > 0
