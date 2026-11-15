# -*- coding: utf-8 -*-
"""B-521: el Patrón geométrico con cilindros que se tocan justo daba «ok» con aristas de más de dos caras (material de
espesor cero, check_geometry: non_manifold_edges > 0), directo o por set_parameter. Ahora es un error de un renglón."""
from omnicad import api


def _sesion(objeto="cylinder"):
    s = api.Sesion()
    assert api.llamar(s, "create_parameter", {"name": "t", "expression": "5 mm"})["ok"]
    assert api.llamar(s, "create_box", {"length": 40, "width": 20, "height": 10})["ok"]
    r = api.llamar(s, "create_geometric_pattern", {"faces": ">Z", "object_type": objeto, "size1": "t", "size2": "t",
                                                   "distance": 6})
    assert r["ok"], r
    return s


def _sano(s):
    (cuerpo,) = api.llamar(s, "check_geometry", {})["result"]["bodies"]
    return cuerpo["valid"] and cuerpo["non_manifold_edges"] == 0


def test_cilindros_que_se_tocan_justo_son_un_error_de_un_renglon():
    s = _sesion()
    for v in ("5.99 mm", "6.01 mm"):                                        # al lado: sanos
        assert api.llamar(s, "set_parameter", {"name": "t", "expression": v})["ok"] and _sano(s)
    r = api.llamar(s, "set_parameter", {"name": "t", "expression": "6 mm"})
    assert not r["ok"] and r["mensaje"].endswith("Dos copias se tocan justo: espesor cero."), r
    assert _sano(s)                                                          # quedó como estaba


def test_esferas_que_se_tocan_en_un_punto_siguen_andando():
    s = _sesion("sphere")
    assert api.llamar(s, "set_parameter", {"name": "t", "expression": "6 mm"})["ok"] and _sano(s)
