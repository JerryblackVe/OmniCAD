# -*- coding: utf-8 -*-
"""Fase 9 · cola del Boceto 3D: Intersection Curve y Project To Surface siguen al modelo, cota angular 3D con
parámetros y sketch_from_spec con las curvas 3D."""
import math

import numpy as np
import pytest

from omnicad import api


@pytest.fixture
def s():
    return api.Sesion()


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _entidades(s, sketch):
    return {e["id"]: e for e in llamar(s, "get_sketch", sketch=sketch)["entities_3d"]}


def _resultado(s, sketch):
    i = next(k for k, op in enumerate(s.doc.operaciones) if op.nombre == sketch)
    return s.doc.resultados[i]


def test_intersect_curves_sigue_al_radio_del_cilindro(s):
    llamar(s, "create_parameter", name="r", expression="10 mm")
    llamar(s, "create_cylinder", radius="r", height=40, z=-20)
    plano = llamar(s, "create_construction_plane", type="angle", references=["X"], angle=45)["plane"]["id"]
    llamar(s, "create_sketch", plane="XY", name="Corte")
    (cid,) = llamar(s, "intersect_curves", faces=["%CYLINDER"], references=[plano])["entities"]
    assert _entidades(s, "Corte")[cid]["minor_radius"] == pytest.approx(10)
    llamar(s, "set_parameter", name="r", expression="15 mm")
    e = _entidades(s, "Corte")[cid]                                     # mismo id, recalculada
    assert e["type"] == "ellipse" and e["minor_radius"] == pytest.approx(15)
    assert np.linalg.norm(e["major_axis"]) == pytest.approx(15 * math.sqrt(2))
    llamar(s, "suppress_feature", feature=s.doc.operaciones[0].id)     # sin el cilindro: aviso y queda la guardada
    assert _entidades(s, "Corte")[cid]["minor_radius"] == pytest.approx(10)
    assert _resultado(s, "Corte").estado == "aviso"


def test_project_to_surface_sigue_a_la_altura_de_la_caja(s):
    llamar(s, "create_parameter", name="h", expression="10 mm")
    llamar(s, "create_box", length=40, width=40, height="h")
    plano = llamar(s, "create_construction_plane", plane="XY", offset=30)["plane"]["id"]
    llamar(s, "create_sketch", plane=plano, name="Fuente")
    circ = llamar(s, "draw_circle", center_x=0, center_y=0, radius=5)["entities"][0]["id"]
    llamar(s, "create_sketch", plane="XY", name="Destino")
    ids = llamar(s, "project_to_surface", faces=[">Z"], curves=[{"sketch": "Fuente", "curve": circ}],
                 mode="closest")["entities"]
    llamar(s, "set_parameter", name="h", expression="15 mm")
    e = _entidades(s, "Destino")
    pts = np.vstack([np.array(e[i]["vertices"]) for i in ids])
    assert np.allclose(pts[:, 2], 15, atol=1e-6)
    assert sum(e[i]["length"] for i in ids) == pytest.approx(10 * math.pi, rel=1e-3)


def test_cota_angular_3d_con_parametro_y_unidades(s):
    llamar(s, "create_parameter", name="ang", expression="30 deg", kind="angle")
    llamar(s, "create_sketch", plane="XY", name="B")
    a = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[10, 0, 0])["entity"]
    c = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[0, 10, 0])["entity"]
    llamar(s, "add_constraint_3d", type="fix", entities=[a])
    llamar(s, "add_dimension_3d", entities=[a, c], value="ang", type="angle")
    op = s.doc.operaciones[-1]
    (k,) = op.boceto.geo3d["cotas"]
    op.boceto.geo3d["cotas"][k]["expresion"] = "ang + 15 deg"            # receta con unidades de ángulo
    llamar(s, "recompute_all")
    e = _entidades(s, "B")
    d = np.subtract(e[c]["end"], e[c]["start"])
    assert math.degrees(math.acos(d[0] / np.linalg.norm(d))) == pytest.approx(45, abs=1e-3)
    op.boceto.geo3d["cotas"][k]["expresion"] = "(60*1.0)"               # lo que guardaban las recetas anteriores
    llamar(s, "recompute_all")
    e = _entidades(s, "B")
    d = np.subtract(e[c]["end"], e[c]["start"])
    assert math.degrees(math.acos(d[0] / np.linalg.norm(d))) == pytest.approx(60, abs=1e-3)


def test_sketch_from_spec_con_curvas_3d(s):
    r = llamar(s, "sketch_from_spec", name="Spec3D", entities=[
        {"type": "arc_3d", "id": "a", "start": [10, 0, 0], "through": [0, 0, 10], "end": [-10, 0, 0]},
        {"type": "circle_3d", "id": "c", "center": [0, 0, 20], "radius": 4, "normal": [1, 0, 0]},
        {"type": "ellipse_3d", "id": "el", "center": [0, 0, 0], "major_end": [0, 6, 0], "minor_radius": 2},
        {"type": "rectangle_3d", "id": "r", "corner": [0, 0, 5], "opposite": [4, 9, 3], "plane": "xy"},
        {"type": "conic_3d", "id": "k", "start": [0, 0, 0], "shoulder": [5, 5, 5], "end": [10, 0, 0], "rho": 0.4},
        {"type": "text_3d", "id": "t", "text": "Hi", "origin": [0, 0, 0], "height": 5, "plane": "zx"},
        {"type": "line_3d", "id": "l", "start": [0, 0, 0], "end": [0, 0, 7]},
        {"type": "spline_3d", "id": "s", "points": [[0, 0, 7], [3, 3, 9], [6, 0, 12]]},
        {"type": "point_3d", "id": "p", "at": [1, 2, 3]},
    ])
    h = r["handles"]
    e = _entidades(s, "Spec3D")
    assert e[h["a"]]["type"] == "arc" and e[h["a"]]["radius"] == pytest.approx(10)
    assert e[h["a"]]["length"] == pytest.approx(10 * math.pi, rel=1e-6)
    assert e[h["c"]]["radius"] == pytest.approx(4) and e[h["c"]]["length"] == pytest.approx(8 * math.pi, rel=1e-5)
    assert e[h["el"]]["minor_radius"] == pytest.approx(2) and np.linalg.norm(e[h["el"]]["major_axis"]) == pytest.approx(6)
    assert sorted(e[h[f"r.l{i}"]]["length"] for i in range(1, 5)) == pytest.approx([4, 4, 9, 9])
    assert e[h["k"]]["rho"] == 0.4 and e[h["t"]]["text"] == "Hi"
    assert e[h["l"]]["length"] == pytest.approx(7) and e[h["s"]]["type"] == "spline"
    assert llamar(s, "get_sketch", sketch="Spec3D")["points_3d"]
    bad = api.llamar(s, "sketch_from_spec", {"entities": [{"type": "circle_3d", "center": [0, 0], "radius": 1}]})
    assert not bad["ok"] and bad["error_kind"] == "INVALID_SPEC"
