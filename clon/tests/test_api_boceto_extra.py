"""Regresiones de espiral, polígono, alargar, partir y arco tangente en la API."""
import inspect
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.perfiles import aristas_boceto
from omnicad.restricciones.boceto import puntos_espiral


def llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture
def s():
    sesion = api.Sesion()
    llamar(sesion, "create_sketch", name="Base")
    return sesion


def linea(sesion, inicio, fin):
    return llamar(sesion, "draw_line", start_x=inicio[0], start_y=inicio[1],
                  end_x=fin[0], end_y=fin[1])["entities"][0]["id"]


def comprobar_deshacer(sesion, antes, pila):
    assert len(sesion.doc._deshacer) == pila + 1
    llamar(sesion, "undo")
    assert sesion.doc.a_dict() == antes


def comprobar_aristas(sesion):
    br = sesion.doc.estado_final.bocetos[sesion.doc.operaciones[0].id]
    aristas = aristas_boceto(br.boceto.geometria(incluir_construccion=True), br.plano)
    assert aristas
    assert all(geo.es_valida(a) for _, a in aristas)


@pytest.mark.parametrize("construccion", [False, True])
def test_espiral_radio_paso_y_deshacer(s, construccion):
    antes, pila = s.doc.a_dict(), len(s.doc._deshacer)
    r = llamar(s, "draw_spiral", sketch="Base", center=[2, 3], start=[7, 3], turns=2,
               pitch=3, construction=construccion)
    assert len(r["entities"]) == 1 and len(r["points"]) == 17
    e = llamar(s, "get_sketch")["entities"][0]
    assert e["type"] == "spline" and e["degree"] == 3 and not e["closed"]
    assert e["construction"] is construccion
    assert e["vertices"][0] == [7, 3]
    assert math.dist(e["vertices"][8], [2, 3]) == pytest.approx(8)
    assert math.dist(e["vertices"][-1], [2, 3]) == pytest.approx(11)
    if not construccion:
        comprobar_aristas(s)
    comprobar_deshacer(s, antes, pila)


def test_puntos_espiral_fraccion_y_paso_negativo():
    pts = puntos_espiral((2, 3), (2, 8), 0.5, -2)
    assert len(pts) == 5
    assert pts[0] == pytest.approx((2, 8))
    assert pts[-1] == pytest.approx((2, -1))


def test_alargar_hasta_el_borde_y_deshacer(s):
    cid = linea(s, (0, 0), (5, 0))
    linea(s, (10, -3), (10, 3))
    antes, pila = s.doc.a_dict(), len(s.doc._deshacer)
    r = llamar(s, "extend_sketch_curve", sketch="Base", curve=cid, point=[4, 0])
    assert r["status"] != "over_constrained"
    e = next(e for e in llamar(s, "get_sketch")["entities"] if e["id"] == cid)
    assert e["end"] == [10, 0] and e["length"] == pytest.approx(10)
    comprobar_aristas(s)
    comprobar_deshacer(s, antes, pila)


def test_partir_conserva_longitud_y_deshacer(s):
    cid = linea(s, (0, 0), (10, 0))
    linea(s, (4, -3), (4, 3))
    antes, pila = s.doc.a_dict(), len(s.doc._deshacer)
    r = llamar(s, "split_sketch_curve", sketch="Base", curve=cid, point=[2, 0])
    assert len(r["pieces"]) == 2 and cid in r["pieces"]
    partes = [e for e in llamar(s, "get_sketch")["entities"] if e["id"] in r["pieces"]]
    assert sorted(e["length"] for e in partes) == pytest.approx([4, 6])
    assert sum(e["length"] for e in partes) == pytest.approx(10)
    comprobar_aristas(s)
    comprobar_deshacer(s, antes, pila)


@pytest.mark.parametrize("un_lado", [False, True])
def test_restriccion_poligono_y_deshacer(s, un_lado):
    r = llamar(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=10)
    ids = [e["id"] for e in r["entities"]]
    antes, pila = s.doc.a_dict(), len(s.doc._deshacer)
    r = llamar(s, "add_constraint", sketch="Base", type="polygon", entities=ids[:1] if un_lado else ids)
    assert r["constraint"]["type"] == "polygon" and len(r["constraint"]["entities"]) == 4
    assert r["status"] != "over_constrained"
    perfil = llamar(s, "get_sketch")["profiles"][0]
    assert perfil["area"] == pytest.approx(100)
    comprobar_aristas(s)
    comprobar_deshacer(s, antes, pila)


@pytest.mark.parametrize("inicio, fin", [((10, 0), (15, 5)), ((10, 0), (15, -5)), ((0, 0), (-5, 5))])
def test_arco_tangente_radio_union_y_deshacer(s, inicio, fin):
    cid = linea(s, (0, 0), (10, 0))
    antes, pila = s.doc.a_dict(), len(s.doc._deshacer)
    r = llamar(s, "draw_arc", sketch="Base", tangent_to=cid, start_x=inicio[0], start_y=inicio[1],
               end_x=fin[0], end_y=fin[1])
    assert r["status"] != "over_constrained"
    assert r["constraints"][0]["type"] == "tangent"
    info = llamar(s, "get_sketch")
    ln, arco = info["entities"]
    assert set(ln["points"]) & set(arco["points"])
    assert arco["radius"] == pytest.approx(5)
    assert arco["center"][0] == pytest.approx(inicio[0])
    assert fin in (tuple(arco["start"]), tuple(arco["end"]))
    comprobar_aristas(s)
    comprobar_deshacer(s, antes, pila)


@pytest.mark.parametrize("nombre, args, kind", [
    ("draw_spiral", {"center": [0, 0], "start": [1, 0], "turns": 0, "pitch": 2}, "INVALID_GEOMETRY"),
    ("draw_spiral", {"center": [0], "start": [1, 0], "turns": 2, "pitch": 2}, "INVALID_GEOMETRY"),
    ("draw_spiral", {"center": [0, 0], "start": [0, 0], "turns": 2, "pitch": 0}, "INVALID_GEOMETRY"),
    ("draw_spiral", {"center": [0, 0], "start": [1, 0], "turns": 1e9, "pitch": 2}, "INVALID_ARGUMENTS"),
    ("draw_spiral", {"center": [0, 0], "start": [1, 0], "turns": 2, "pitch": math.inf}, "INVALID_ARGUMENTS"),
    ("extend_sketch_curve", {"curve": 999, "point": [5, 0]}, "ENTITY_NOT_FOUND"),
    ("extend_sketch_curve", {"curve": 3, "point": [5, 0]}, "INVALID_GEOMETRY"),
    ("split_sketch_curve", {"curve": 999, "point": [5, 0]}, "ENTITY_NOT_FOUND"),
    ("split_sketch_curve", {"curve": 3, "point": [5, 1]}, "INVALID_GEOMETRY"),
    ("split_sketch_curve", {"curve": 3, "point": [5, 0]}, "INVALID_GEOMETRY"),
    ("add_constraint", {"type": "polygon", "entities": [3]}, "INVALID_CONSTRAINT"),
    ("add_constraint", {"type": "polygon", "entities": [999]}, "ENTITY_NOT_FOUND"),
    ("draw_arc", {"tangent_to": 999, "start_x": 10, "start_y": 0, "end_x": 15, "end_y": 5}, "ENTITY_NOT_FOUND"),
    ("draw_arc", {"tangent_to": 3, "start_x": 5, "start_y": 0, "end_x": 15, "end_y": 5}, "INVALID_GEOMETRY"),
    ("draw_arc", {"tangent_to": 3, "start_x": 10, "start_y": 0, "end_x": 15, "end_y": 0}, "INVALID_GEOMETRY"),
    ("draw_arc", {"tangent_to": 3, "start_x": 10, "start_y": 0}, "INVALID_ARGUMENTS"),
])
def test_errores_atomicos(s, nombre, args, kind):
    assert linea(s, (0, 0), (10, 0)) == 3
    antes, pila = s.doc.a_dict(), len(s.doc._deshacer)
    r = api.llamar(s, nombre, {"sketch": "Base", **args})
    assert not r["ok"] and r["error_kind"] == kind, r
    assert s.doc.a_dict() == antes and len(s.doc._deshacer) == pila


def test_parametros_documentados_y_registro():
    from omnicad.api.registro import _CATALOGO

    for nombre in ("draw_spiral", "extend_sketch_curve", "split_sketch_curve", "draw_arc", "add_constraint"):
        h = _CATALOGO[nombre]
        assert h.grupo == "boceto" and h.modifica
        nombres = list(inspect.signature(h.funcion).parameters)[1:]
        assert len(nombres) == len(h.esquema["properties"])
        assert all(h.esquema["properties"][p].get("description") for p in nombres)
