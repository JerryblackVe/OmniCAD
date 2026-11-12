# -*- coding: utf-8 -*-
"""B-308: Combinar › Unir del buje roscado y la tapa de la pieza de Gerardo perdía 2386 mm³ con un aviso amarillo y la
previa dejaba Aceptar; el error decía «probá mover la pieza una milésima» (Gerardo la subió 0,1 mm y quedó peor) y
mandaba a `check_geometry`, que en la ventana es Inspeccionar › Revisar geometría."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _volumen(s, cuerpo):
    return _ok(s, "get_physical_properties", bodies=[cuerpo])["bodies"][0]["volume"]


def test_unir_las_mitades_del_buje_roscado_y_la_tapa():
    """Guardia con el caso rearmado (tapa partida justo donde termina la rosca interior del buje): en main une bien."""
    s = api.Sesion()
    _ok(s, "create_cylinder", height=5, radius=22.5, name="Tapa")
    _ok(s, "create_cylinder", height=15, radius=15.5, z=-15, operation="join", target="Tapa")
    _ok(s, "create_cylinder", height=15, radius=14, z=-15, name="Eje")
    _ok(s, "create_thread", faces=["%CYLINDER"], body="Eje", thread="M28")
    _ok(s, "boolean_operation", target="Tapa", tools=["Eje"], operation="cut", keep_tools=True)
    entero = _volumen(s, "Tapa")
    _ok(s, "create_construction_plane", plane="XY", offset=0, name="P")
    _ok(s, "split_body", body="Tapa", tool="P")
    buje = next(b["id"] for b in _ok(s, "get_scene_info")["bodies"] if b["name"] not in ("Tapa", "Eje"))
    assert _volumen(s, "Tapa") == pytest.approx(math.pi * 22.5 ** 2 * 5, rel=1e-6)
    _ok(s, "boolean_operation", target="Tapa", tools=[buje], operation="join")
    revision = _ok(s, "check_geometry", body="Tapa")["bodies"][0]
    assert revision["closed"] and revision["free_edges"] == 0
    assert revision["volume"] == pytest.approx(entero, rel=1e-6)


def test_una_union_que_pierde_material_falla_y_no_deja_aceptar(monkeypatch):
    s = api.Sesion()
    _ok(s, "create_box", length=10, width=10, height=10, name="A")
    real = geo.booleano
    monkeypatch.setattr(geo, "booleano", lambda o, h, op, avisos=None: real(o, h, "cortar" if op == "unir" else op))
    r = api.llamar(s, "create_box", {"length": 5, "width": 5, "height": 5, "x": 8, "operation": "join", "target": "A"})
    assert not r["ok"] and "perdió" in r["mensaje"]
    assert "milésima" not in r["mensaje"] and "al menos 0,1 mm" in r["mensaje"]
    assert _volumen(s, "A") == pytest.approx(1000)        # el documento quedó como estaba
