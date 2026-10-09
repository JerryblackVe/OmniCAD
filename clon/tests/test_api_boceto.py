# -*- coding: utf-8 -*-
import json
import math

import pytest

from omnicad import api


@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def foto(sesion):
    """Todo lo que una falla atómica no debe cambiar."""
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado)


def entidades(sesion, sketch=None):
    return {e["id"]: e for e in llamar(sesion, "get_sketch", sketch=sketch)["entities"]}


HERRAMIENTAS = ["create_construction_plane", "create_sketch", "draw_line", "draw_rectangle", "draw_circle", "draw_arc",
                "create_polygon", "draw_spline", "add_constraint", "add_dimension", "get_sketch", "sketch_from_spec"]


def test_herramientas_del_grupo_boceto():
    assert [h["nombre"] for h in api.catalogo("boceto")] == HERRAMIENTAS
    lecturas = {h["nombre"] for h in api.catalogo("boceto") if not h["modifica"]}
    assert lecturas == {"get_sketch"}


# ---------------------------------------------------------------- planos y bocetos vacíos
def test_marcos_de_los_planos_de_origen(s):
    marcos = {}
    for plano in ("XY", "XZ", "YZ"):
        marcos[plano] = llamar(s, "create_sketch", plane=plano.lower())["plane_frame"]
    assert marcos["XY"]["u_axis"] == [1, 0, 0] and marcos["XY"]["v_axis"] == [0, 1, 0]
    assert marcos["XZ"]["u_axis"] == [1, 0, 0] and marcos["XZ"]["v_axis"] == [0, 0, 1]
    assert marcos["XZ"]["normal"] == [0, -1, 0]
    assert marcos["YZ"]["u_axis"] == [0, 1, 0] and marcos["YZ"]["v_axis"] == [0, 0, 1]
    assert marcos["YZ"]["normal"] == [1, 0, 0]
    assert [b["name"] for b in llamar(s, "get_scene_info")["sketches"]] == ["Boceto1", "Boceto2", "Boceto3"]


def test_plano_de_construccion_y_boceto_sobre_el(s):
    plano = llamar(s, "create_construction_plane", plane="XY", offset=12, name="Alto")
    assert plano["origin"] == [0, 0, 12] and plano["plane"]["name"] == "Alto" and plano["normal"] == [0, 0, 1]
    otro = llamar(s, "create_construction_plane", plane="alto", offset="8 mm / 2")           # desde otro plano, por nombre
    assert otro["origin"] == [0, 0, 16]
    boceto = llamar(s, "create_sketch", plane="Alto", name="Arriba")
    assert boceto["plane"] == plano["plane"]["id"] and boceto["plane_frame"]["origin"] == [0, 0, 12]
    r = api.llamar(s, "create_sketch", {"plane": "Cielo"})
    assert r["error_kind"] == "PLANE_NOT_FOUND" and any("XY" in p for p in r["pistas"])
    assert api.llamar(s, "create_construction_plane", {"plane": "ZZ"})["error_kind"] == "PLANE_NOT_FOUND"


def test_plano_de_construccion_con_parametro(s):
    llamar(s, "create_parameter", name="h", expression="30 mm")
    llamar(s, "create_construction_plane", plane="XZ", offset="h / 2", name="P")
    assert llamar(s, "create_sketch", plane="P")["plane_frame"]["origin"] == [0, -15, 0]    # normal de XZ = −Y
    llamar(s, "set_parameter", name="h", expression="40 mm")
    assert llamar(s, "get_sketch")["plane_frame"]["origin"] == [0, -20, 0]


def test_sketch_no_encontrado(s):
    assert api.llamar(s, "draw_circle", {"radius": 1})["error_kind"] == "SKETCH_NOT_FOUND"
    llamar(s, "create_sketch", name="Base")
    r = api.llamar(s, "get_sketch", {"sketch": "Bsae"})
    assert r["error_kind"] == "SKETCH_NOT_FOUND" and "Base" in r["pistas"][0]
    llamar(s, "create_parameter", name="p", expression="1 mm")
    assert api.llamar(s, "get_sketch", {"sketch": "op1"})["ok"]
    # un paso que no es un boceto
    llamar(s, "create_construction_plane", name="Pl")
    r = api.llamar(s, "get_sketch", {"sketch": "Pl"})
    assert r["error_kind"] == "SKETCH_NOT_FOUND"
    r = api.llamar(s, "get_sketch", {"sketch": "op2"})
    assert r["error_kind"] == "SKETCH_NOT_FOUND" and "plano" in r["mensaje"]


# ---------------------------------------------------------------- dibujar
def test_linea_circulo_y_perfiles(s):
    llamar(s, "create_sketch")
    r = llamar(s, "draw_rectangle", x1=0, y1=0, x2=60, y2=40)
    assert [e["type"] for e in r["entities"]] == ["line"] * 4 and len(r["points"]) == 4
    assert r["profiles"] == 1 and {c["type"] for c in r["constraints"]} == {"horizontal", "vertical"}
    c = llamar(s, "draw_circle", radius=6, center_x=30, center_y=20)
    assert c["profiles"] == 2 and c["entities"][0]["type"] == "circle"
    info = llamar(s, "get_sketch")
    areas = sorted(p["area"] for p in info["profiles"])
    assert areas == pytest.approx([math.pi * 36, 60 * 40 - math.pi * 36], abs=1e-3)
    anillo = max(info["profiles"], key=lambda p: p["area"])
    assert anillo["bounding_box"] == {"min": [0, 0], "max": [60, 40]} and anillo["centroid"] == pytest.approx([30, 20], abs=1e-3)
    assert len(anillo["curves"]) == 5
    disco = min(info["profiles"], key=lambda p: p["area"])
    assert disco["bounding_box"] == {"min": [24, 14], "max": [36, 26]}
    assert [p["index"] for p in info["profiles"]] == [0, 1]


def test_tres_formas_de_rectangulo(s):
    llamar(s, "create_sketch")
    llamar(s, "draw_rectangle", x1=10, y1=10, x2=0, y2=0)                      # esquinas en cualquier orden
    llamar(s, "draw_rectangle", center_x=50, center_y=5, width=20, height=6)
    llamar(s, "draw_rectangle", origin_x=100, origin_y=-3, width=8, height=4)
    cajas = sorted((p["bounding_box"]["min"], p["bounding_box"]["max"]) for p in llamar(s, "get_sketch")["profiles"])
    assert cajas == [([0, 0], [10, 10]), ([40, 2], [60, 8]), ([100, -3], [108, 1])]
    assert api.llamar(s, "draw_rectangle", {"width": 5})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 5})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 0, "y2": 5})["error_kind"] == "INVALID_GEOMETRY"


def test_lineas_de_construccion_no_forman_perfiles(s):
    llamar(s, "create_sketch")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=10, construction=True)
    assert llamar(s, "get_sketch")["profiles"] == []
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=5, end_y=5)
    e = llamar(s, "get_sketch")["entities"]
    assert sum(1 for x in e if x["construction"]) == 4 and e[-1]["type"] == "line" and e[-1]["length"] == pytest.approx(7.0711, abs=1e-3)


def test_arcos(s):
    llamar(s, "create_sketch")
    a = llamar(s, "draw_arc", start_x=10, start_y=0, center_x=0, center_y=0, sweep_angle=90)["entities"][0]["id"]
    b = llamar(s, "draw_arc", start_x=10, start_y=0, center_x=0, center_y=0, sweep_angle=-90)["entities"][0]["id"]
    c = llamar(s, "draw_arc", start_x=0, start_y=0, mid_x=5, mid_y=5, end_x=10, end_y=0)["entities"][0]["id"]
    e = entidades(s)
    assert (e[a]["start"], e[a]["end"], e[a]["radius"]) == ([10, 0], [0, 10], 10)
    assert (e[b]["start"], e[b]["end"]) == ([0, -10], [10, 0])                 # horario: se guarda antihorario
    assert (e[c]["center"], e[c]["radius"]) == ([5, 0], 5)
    for args in ({"start_x": 1, "start_y": 1}, {"start_x": 1, "start_y": 1, "center_x": 0, "center_y": 0}):
        assert api.llamar(s, "draw_arc", args)["error_kind"] == "INVALID_ARGUMENTS"
    for barrido in (0, 360, 400):
        r = api.llamar(s, "draw_arc", {"start_x": 5, "start_y": 0, "center_x": 0, "center_y": 0, "sweep_angle": barrido})
        assert r["error_kind"] == "INVALID_GEOMETRY"
    r = api.llamar(s, "draw_arc", {"start_x": 0, "start_y": 0, "mid_x": 5, "mid_y": 0, "end_x": 10, "end_y": 0})
    assert r["error_kind"] == "INVALID_GEOMETRY"                                # tres puntos alineados


@pytest.mark.parametrize("lados, circunscrito, area", [
    (6, False, 3 * 100 * math.sin(math.pi / 3)),
    (5, True, 5 * 100 * math.tan(math.pi / 5)),
    (3, False, 1.5 * 100 * math.sin(2 * math.pi / 3)),
])
def test_poligono_regular(s, lados, circunscrito, area):
    llamar(s, "create_sketch")
    r = llamar(s, "create_polygon", sides=lados, radius=10, center_x=5, center_y=-2, rotation=15,
               kind="circumscribed" if circunscrito else "inscribed")
    assert r["profiles"] == 1 and sum(1 for x in r["entities"] if x["type"] == "line") == lados
    perfil = llamar(s, "get_sketch")["profiles"][0]
    assert perfil["area"] == pytest.approx(area, abs=1e-2) and perfil["centroid"] == pytest.approx([5, -2], abs=1e-3)
    assert api.llamar(s, "create_polygon", {"sides": 2, "radius": 3})["error_kind"] == "INVALID_GEOMETRY"
    assert api.llamar(s, "create_polygon", {"sides": 4, "radius": 0})["error_kind"] == "INVALID_GEOMETRY"


def test_splines(s):
    llamar(s, "create_sketch")
    sp = llamar(s, "draw_spline", points=[[0, 0], [10, 5], [20, 0], [30, 8]])
    assert sp["entities"][0]["type"] == "spline" and sp["profiles"] == 0
    ctl = llamar(s, "draw_spline", points=[[0, 20], [10, 25], [20, 20], [30, 28]], spline_type="control_points")
    cerrada = llamar(s, "draw_spline", points=[[0, 40], [10, 50], [20, 40], [10, 30]], closed=True)
    assert cerrada["profiles"] == 1
    e = entidades(s)
    assert e[ctl["entities"][0]["id"]]["spline_type"] == "control_points" and e[cerrada["entities"][0]["id"]]["closed"]
    assert api.llamar(s, "draw_spline", {"points": [[0, 0]]})["error_kind"] == "INVALID_GEOMETRY"
    assert api.llamar(s, "draw_spline", {"points": [[0, 0], [1, 1]], "spline_type": "control_points"})["error_kind"] \
        == "INVALID_GEOMETRY"
    assert api.llamar(s, "draw_spline", {"points": [[0, 0], [1]]})["error_kind"] == "INVALID_GEOMETRY"


def test_deshacer_un_dibujo_es_un_paso(s):
    llamar(s, "create_sketch")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    pila = len(s.doc._deshacer)
    antes = foto(s)[0]
    n_antes = len(entidades(s))
    for nombre, args in (("draw_circle", {"radius": 3, "center_x": 10, "center_y": 5}),
                         ("draw_line", {"start_x": 0, "start_y": 0, "end_x": 20, "end_y": 10}),
                         ("create_polygon", {"sides": 6, "radius": 2, "center_x": 5, "center_y": 5}),
                         ("draw_spline", {"points": [[0, 0], [5, 5], [10, 0]]})):
        ok(api.llamar(s, nombre, args))
        assert len(s.doc._deshacer) == pila + 1                                # un solo paso de deshacer
        assert len(entidades(s)) > n_antes
        ok(api.llamar(s, "undo"))
        assert len(entidades(s)) == n_antes and foto(s)[0] == antes
    # el OpBoceto del timeline no se mutó en el lugar: lo viejo sigue siendo el viejo
    op = s.doc.operaciones[0]
    ok(api.llamar(s, "draw_circle", {"radius": 1}))
    assert s.doc.operaciones[0] is not op and len(op.boceto.curvas) == 4
    ok(api.llamar(s, "undo"))
    ok(api.llamar(s, "redo"))
    assert len(entidades(s)) == n_antes + 1


def test_dibujar_en_un_boceto_por_nombre_y_el_ultimo(s):
    llamar(s, "create_sketch", name="A")
    llamar(s, "create_sketch", name="B")
    llamar(s, "draw_circle", radius=2)                                         # sin sketch: el último (B)
    llamar(s, "draw_circle", radius=3, sketch="a")
    assert len(entidades(s, "A")) == 1 and len(entidades(s, "B")) == 1
    assert entidades(s, "A")[1]["radius"] == 3 and entidades(s, "B")[1]["radius"] == 2


# ---------------------------------------------------------------- restricciones y cotas
def _placa(s):
    llamar(s, "create_sketch", name="P")
    return llamar(s, "draw_rectangle", x1=0, y1=0, x2=50, y2=30)


def test_restricciones_y_cotas_con_parametros(s):
    llamar(s, "create_parameter", name="ancho", expression="60 mm")
    r = _placa(s)
    bajo, derecha, arriba = (e["id"] for e in r["entities"][:3])
    p1 = r["points"][0]
    assert api.llamar(s, "add_constraint", {"sketch": "P", "type": "fix", "entities": [p1]})["ok"]
    d = llamar(s, "add_dimension", sketch="P", type="distance", entities=[bajo], value="ancho")
    assert d["dimension"]["value"] == 60 and d["dof"] == 1 and d["status"] == "under_constrained"
    d = llamar(s, "add_dimension", sketch="P", type="distance", entities=[derecha], value=30)
    assert d["dof"] == 0 and d["status"] == "fully_constrained"
    assert entidades(s)[bajo]["end"] == [60, 0]
    llamar(s, "set_parameter", name="ancho", expression="80 mm")
    assert entidades(s)[bajo]["end"] == [80, 0] and llamar(s, "get_sketch")["profiles"][0]["area"] == pytest.approx(2400, abs=1e-3)
    dims = llamar(s, "get_sketch")["dimensions"]
    assert [(k["type"], k["expression"], k["value"]) for k in dims] == [("distance", "ancho", 80), ("distance", "30.0", 30)]
    assert [k["type"] for k in llamar(s, "get_sketch")["constraints"]][-1] == "fix"
    assert llamar(s, "get_sketch")["points"][0]["fixed"] is True
    # cota sin valor: usa la medida actual
    sin_valor = llamar(s, "add_dimension", sketch="P", type="distance", entities=[arriba])
    assert sin_valor["dimension"]["value"] == pytest.approx(80, abs=1e-6) and sin_valor["status"] == "fully_constrained"


def test_circulo_cotado_y_angulo(s):
    llamar(s, "create_sketch")
    c = llamar(s, "draw_circle", radius=4, center_x=10, center_y=10)["entities"][0]["id"]
    d = llamar(s, "add_dimension", sketch="Boceto1", type="diameter", entities=[c], value=12)
    assert entidades(s)[c]["radius"] == 6 and d["dimension"]["value"] == 12
    l1 = llamar(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    l2 = llamar(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=10)["entities"][0]["id"]
    llamar(s, "add_constraint", sketch="Boceto1", type="coincident", entities=[entidades(s)[l2]["points"][0],
                                                                             entidades(s)[l1]["points"][0]])
    a = llamar(s, "add_dimension", sketch="Boceto1", type="angle", entities=[l1, l2], value="60 deg")
    assert a["dimension"]["value"] == 60 and a["dimension"]["type"] == "angle"


def test_errores_de_restricciones_y_cotas(s):
    bajo = _placa(s)["entities"][0]["id"]
    antes = foto(s)
    casos = [("add_constraint", {"sketch": "P", "type": "horizontal", "entities": [9999]}, "ENTITY_NOT_FOUND"),
             ("add_constraint", {"sketch": "P", "type": "parallel", "entities": [bajo]}, "INVALID_CONSTRAINT"),
             ("add_constraint", {"sketch": "P", "type": "tangent", "entities": [bajo, bajo]}, "INVALID_CONSTRAINT"),
             ("add_constraint", {"sketch": "P", "type": "parabola", "entities": [bajo]}, "INVALID_ARGUMENTS"),
             ("add_constraint", {"sketch": "Q", "type": "fix", "entities": [1]}, "SKETCH_NOT_FOUND"),
             ("add_dimension", {"sketch": "P", "type": "radius", "entities": [bajo], "value": 3}, "INVALID_DIMENSION"),
             ("add_dimension", {"sketch": "P", "type": "distance", "entities": [bajo], "value": "sin_parametro"},
              "INVALID_EXPRESSION"),
             ("add_dimension", {"sketch": "P", "type": "distance", "entities": [9999], "value": 3}, "ENTITY_NOT_FOUND"),
             ("add_dimension", {"sketch": "P", "type": "distance", "entities": [bajo], "value": "5 deg"},
              "UNIT_MISMATCH")]
    for nombre, args, kind in casos:
        r = api.llamar(s, nombre, args)
        assert r["error_kind"] == kind, (nombre, args, r)
        assert foto(s) == antes
    # conflicto: dos cotas incompatibles → atómico
    llamar(s, "add_dimension", sketch="P", type="distance", entities=[bajo], value=50)
    llamar(s, "add_constraint", sketch="P", type="fix", entities=entidades(s)[bajo]["points"])
    antes = foto(s)
    r = api.llamar(s, "add_dimension", {"sketch": "P", "type": "horizontal", "entities": entidades(s)[bajo]["points"],
                                         "value": 70})
    assert r["error_kind"] == "SKETCH_OVERCONSTRAINED" and "conflicto" in r["mensaje"]
    assert foto(s) == antes


# ---------------------------------------------------------------- sketch_from_spec
SPEC_PLACA = {
    "plane": "XY", "name": "Placa",
    "entities": [{"type": "rectangle", "id": "placa", "corner1": [0, 0], "corner2": [50, 30]},
                 {"type": "circle", "id": "agujero", "center": [25, 15], "radius": 3}],
    "constraints": [{"type": "fix", "entities": ["placa.c1"]}],
    "dimensions": [{"type": "distance", "entities": ["placa.bottom"], "value": "ancho"},
                   {"type": "distance", "entities": ["placa.right"], "value": 30},
                   {"type": "radius", "entities": ["agujero"], "value": "radio_agujero"},
                   {"type": "horizontal", "entities": ["placa.c1", "agujero.center"], "value": "ancho / 2"},
                   {"type": "vertical", "entities": ["placa.c1", "agujero.center"], "value": 15}]}


def test_boceto_completo_en_una_llamada(s):
    llamar(s, "create_parameter", name="ancho", expression="60 mm")
    llamar(s, "create_parameter", name="radio_agujero", expression="5 mm")
    s.doc._deshacer.clear()
    r = llamar(s, "sketch_from_spec", **SPEC_PLACA)
    assert (r["status"], r["dof"], r["profiles"]) == ("fully_constrained", 0, 2)
    assert r["entities"] == 5 and r["constraints"] == 5 and r["dimensions"] == 5
    assert set(r["handles"]) >= {"placa.bottom", "placa.c1", "agujero", "agujero.center"}
    assert len(s.doc._deshacer) == 1                                           # todo el boceto = un paso
    centro = next(p for p in llamar(s, "get_sketch", sketch="Placa")["points"] if p["id"] == r["handles"]["agujero.center"])
    assert (centro["x"], centro["y"]) == (30, 15)
    llamar(s, "set_parameter", name="ancho", expression="40 mm")
    assert llamar(s, "get_sketch", sketch="Placa")["profiles"][1]["area"] == pytest.approx(40 * 30 - math.pi * 25, abs=1e-2)
    ok(api.llamar(s, "undo"))                                                  # deshace set_parameter
    assert llamar(s, "get_sketch", sketch="Placa")["profiles"][1]["area"] == pytest.approx(60 * 30 - math.pi * 25, abs=1e-2)
    ok(api.llamar(s, "undo"))                                                  # un solo deshacer quita el boceto entero
    assert api.llamar(s, "get_sketch", {"sketch": "Placa"})["error_kind"] == "SKETCH_NOT_FOUND"


def test_spec_con_todos_los_tipos_de_entidad(s):
    r = llamar(s, "sketch_from_spec", plane="YZ", entities=[
        {"type": "line", "start": [0, 0], "end": [10, 0], "construction": True},
        {"type": "rectangle", "center": [20, 5], "width": 10, "height": 4},
        {"type": "rectangle", "origin": [40, 0], "width": 5, "height": 5},
        {"type": "arc", "center": [60, 0], "start": [65, 0], "sweep": 180},
        {"type": "arc", "start": [70, 0], "mid": [75, 5], "end": [80, 0]},
        {"type": "polygon", "sides": 6, "radius": 4, "center": [90, 0], "id": "hex"},
        {"type": "spline", "points": [[0, 20], [5, 25], [10, 20]]},
        {"type": "point", "at": [0, 0], "id": "o"}])
    assert r["entities"] > 10 and r["plane"] == "YZ" and "hex.side6" in r["handles"] and "o" in r["handles"]
    assert llamar(s, "get_sketch")["plane_frame"]["u_axis"] == [0, 1, 0]


@pytest.mark.parametrize("spec, kind", [
    ({"entities": [{"type": "triangulo"}]}, "INVALID_SPEC"),
    ({"entities": [{"type": "line", "start": [0, 0]}]}, "INVALID_SPEC"),
    ({"entities": [{"type": "circle", "center": [0, 0], "radius": "x"}]}, "INVALID_SPEC"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"},
                   {"type": "line", "start": [0, 0], "end": [0, 1], "id": "a"}]}, "INVALID_SPEC"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"}],
      "constraints": [{"type": "horizontal", "entities": ["b"]}]}, "INVALID_SPEC"),
    ({"entities": [{"type": "rectangle", "id": "r", "corner1": [0, 0], "corner2": [1, 1]}],
      "constraints": [{"type": "horizontal", "entities": ["r"]}]}, "INVALID_SPEC"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"}],
      "constraints": [{"type": "nada", "entities": ["a"]}]}, "INVALID_CONSTRAINT"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"}],
      "constraints": [{"type": "parallel", "entities": ["a"]}]}, "INVALID_CONSTRAINT"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"}],
      "dimensions": [{"type": "radius", "entities": ["a"], "value": 1}]}, "INVALID_DIMENSION"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"}],
      "dimensions": [{"type": "distance", "entities": ["a"]}]}, "INVALID_DIMENSION"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"}],
      "dimensions": [{"type": "distance", "entities": ["a"], "value": "q"}]}, "INVALID_EXPRESSION"),
    ({"entities": [{"type": "line", "start": [0, 0], "end": [1, 0], "id": "a"}],
      "constraints": [{"type": "vertical", "entities": ["a"]}, {"type": "horizontal", "entities": ["a"]}]},
     "SKETCH_OVERCONSTRAINED"),
    ({"plane": "ZZ"}, "PLANE_NOT_FOUND"),
])
def test_spec_invalido_no_deja_nada(s, spec, kind):
    llamar(s, "create_sketch")
    antes = foto(s)
    r = api.llamar(s, "sketch_from_spec", spec)
    assert r["ok"] is False and r["error_kind"] == kind, r
    assert foto(s) == antes


def test_boceto_con_conflicto_pide_arreglar(s):
    llamar(s, "create_sketch")
    l1 = llamar(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    llamar(s, "add_constraint", sketch="Boceto1", type="horizontal", entities=[l1])
    antes = foto(s)
    r = api.llamar(s, "add_constraint", {"sketch": "Boceto1", "type": "vertical", "entities": [l1]})
    assert r["error_kind"] == "SKETCH_OVERCONSTRAINED"
    assert foto(s) == antes
    assert llamar(s, "get_sketch")["status"] == "under_constrained"
