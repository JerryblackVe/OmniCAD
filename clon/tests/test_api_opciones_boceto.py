# -*- coding: utf-8 -*-
"""Opciones nuevas de herramientas de boceto y construcción (ola 7 de B-80): tipos de plano de construcción
(MCP-39, MCP-70), círculo por 2 y 3 puntos (MCP-72), polígono por arista (MCP-73), línea de punto medio y
rectángulos central y de 3 puntos (MCP-74), proyección de vértices (MCP-75) y radio libre sin cota (MCP-76)."""
import math

import pytest

from omnicad import api


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, esperado="INVALID_ARGUMENTS", **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == esperado, r
    return r


def boceto():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="B")
    return s


def entidades(s):
    return {e["id"]: e for e in ok(s, "get_sketch")["entities"]}


def lineas(s):
    return [e for e in ok(s, "get_sketch")["entities"] if e["type"] == "line"]


# ---------------------------------------------------------------- planos de construcción
def test_plano_en_desfase_de_una_cara_plana_y_planos_por_tres_puntos():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=10, name="Caja")
    r = ok(s, "create_construction_plane", plane=">Z", offset=5)                       # MCP-70
    assert r["origin"][2] == pytest.approx(15) and r["normal"] == pytest.approx([0, 0, 1])
    p1 = ok(s, "create_construction_point", type="vertice", references=[[10, 10, 10]])["point"]["id"]
    p2 = ok(s, "create_construction_point", type="vertice", references=[[-10, 10, 10]])["point"]["id"]
    p3 = ok(s, "create_construction_point", type="vertice", references=[[10, -10, 0]])["point"]["id"]
    r = ok(s, "create_construction_plane", type="three_points", references=[p1, p2, p3])
    n = r["normal"]                                           # los tres puntos están en el plano: contiene al eje X
    assert abs(n[0]) < 1e-9 and math.hypot(n[1], n[2]) == pytest.approx(1, abs=1e-3) and n[2] != 0
    for p in ([10, 10, 10], [-10, 10, 10], [10, -10, 0]):
        assert sum((p[i] - r["origin"][i]) * n[i] for i in range(3)) == pytest.approx(0, abs=1e-3)
    r = ok(s, "create_construction_plane", type="middle", references=["XY", ">Z"], body="Caja")
    assert r["origin"][2] == pytest.approx(5)                                                  # a mitad de camino
    r = ok(s, "create_construction_plane", type="angle", references=["edges:|X and >Z and >Y"], angle=90, body="Caja")
    assert abs(r["normal"][0]) == pytest.approx(0, abs=1e-9)
    falla(s, "create_construction_plane", type="three_points", references=[p1, p2])
    falla(s, "create_construction_plane", type="middle", references=["XY", "no_existe"], esperado="INVALID_ARGUMENTS")


# ---------------------------------------------------------------- círculos
def test_circulo_por_dos_y_tres_puntos():
    s = boceto()
    ok(s, "draw_circle", kind="two_points", points=[[0, 0], [10, 0]])
    ok(s, "draw_circle", kind="three_points", points=[[20, 0], [30, 10], [40, 0]])
    c = entidades(s)
    assert c[1]["center"] == pytest.approx([5, 0]) and c[1]["radius"] == pytest.approx(5)
    segundo = next(e for e in c.values() if e["id"] != 1 and e["type"] == "circle")
    assert segundo["center"] == pytest.approx([30, 0]) and segundo["radius"] == pytest.approx(10)
    falla(s, "draw_circle", kind="two_points", points=[[1, 1], [1, 1]], esperado="INVALID_GEOMETRY")
    falla(s, "draw_circle", kind="three_points", points=[[0, 0], [1, 1], [2, 2]], esperado="INVALID_GEOMETRY")
    falla(s, "draw_circle", kind="three_points", points=[[0, 0], [1, 1]])
    falla(s, "draw_circle", kind="center_radius")
    ok(s, "draw_circle", radius=3, center_x=-20)                                  # la forma de siempre sigue andando


def test_radio_libre_sin_cota_y_con_cota():
    s = boceto()
    ok(s, "draw_circle", radius=5)
    ok(s, "set_circle_radius", sketch="B", curve=1, radius=8)
    assert entidades(s)[1]["radius"] == pytest.approx(8)
    ok(s, "undo")
    assert entidades(s)[1]["radius"] == pytest.approx(5)
    ok(s, "add_dimension", sketch="B", type="radius", entities=[1], value=5)
    falla(s, "set_circle_radius", "INVALID_GEOMETRY", sketch="B", curve=1, radius=9)         # con cota: edit_dimension
    falla(s, "set_circle_radius", "INVALID_GEOMETRY", sketch="B", curve=1, radius=-1)
    linea = ok(s, "draw_line", start_x=0, start_y=0, end_x=5, end_y=0)["entities"][0]["id"]
    falla(s, "set_circle_radius", "INVALID_GEOMETRY", sketch="B", curve=linea, radius=2)         # una línea no es un círculo
    arco = ok(s, "draw_arc", start_x=40, start_y=0, center_x=30, center_y=0, sweep_angle=90)["entities"][0]["id"]
    _centro, inicio, fin = ok(s, "get_sketch")["entities"][-1]["points"]
    ok(s, "set_circle_radius", sketch="B", curve=arco, radius=12)                                  # extremos libres: se corren
    assert entidades(s)[arco]["radius"] == pytest.approx(12)
    ok(s, "add_constraint", sketch="B", type="fix", entities=[inicio])
    ok(s, "add_constraint", sketch="B", type="fix", entities=[fin])
    falla(s, "set_circle_radius", "INVALID_GEOMETRY", sketch="B", curve=arco, radius=20)           # extremos fijos: no dice OK en falso
    assert entidades(s)[arco]["radius"] == pytest.approx(12)


# ---------------------------------------------------------------- polígono por arista
def test_poligono_por_arista():
    s = boceto()
    r = ok(s, "create_polygon", sides=6, kind="edge", edge_points=[[0, 0], [10, 0], [5, 20]])
    assert len(r["entities"]) == 7                                               # circunferencia guía + 6 lados
    ls = lineas(s)
    centros = [e for e in entidades(s).values() if e["type"] == "circle"]
    assert centros[0]["radius"] == pytest.approx(10)                             # hexágono de lado 10: circunradio 10
    assert centros[0]["center"] == pytest.approx([5, 10 * math.sqrt(3) / 2], abs=1e-3)     # del lado de C (hacia +Y)
    assert len(ls) == 6
    falla(s, "create_polygon", sides=6, kind="edge", edge_points=[[0, 0], [0, 0], [5, 5]], esperado="INVALID_GEOMETRY")
    falla(s, "create_polygon", sides=6, kind="edge")
    falla(s, "create_polygon", sides=6)                                           # sin radius y sin edge


# ---------------------------------------------------------------- línea de punto medio y rectángulos
def test_linea_de_punto_medio_y_rectangulos_central_y_de_tres_puntos():
    s = boceto()
    r = ok(s, "draw_line", start_x=0, start_y=5, end_x=10, end_y=5, midpoint=True)
    assert any(c["type"] == "midpoint" for c in ok(s, "get_sketch")["constraints"])
    assert r["points"] and len(r["entities"]) == 1
    # va de (-10, 5) a (10, 5): el primer punto es el punto medio
    ln = ok(s, "get_sketch")
    assert ln["status"] in ("under_constrained", "fully_constrained")
    s2 = boceto()
    ok(s2, "draw_rectangle", center_x=0, center_y=0, width=10, height=6, center_diagonals=True)
    n_lineas = lineas(s2)
    assert len(n_lineas) == 6 and sum(1 for e in n_lineas if e["construction"]) == 2          # + 2 diagonales
    assert any(c["type"] == "midpoint" for c in ok(s2, "get_sketch")["constraints"])
    falla(s2, "draw_rectangle", x1=0, y1=0, x2=5, y2=5, center_diagonals=True)
    s3 = boceto()
    ok(s3, "draw_rectangle", three_points=[[0, 0], [10, 10], [-3, 3]])                          # girado 45°
    assert len(lineas(s3)) == 4
    tipos = {c["type"] for c in ok(s3, "get_sketch")["constraints"]}
    assert {"perpendicular", "parallel"} <= tipos
    falla(s3, "draw_rectangle", three_points=[[0, 0], [10, 0], [5, 0]], esperado="INVALID_GEOMETRY")   # ancho cero
    falla(s3, "draw_rectangle", three_points=[[0, 0], [10, 0]])
    falla(s3, "draw_rectangle", x1=0, y1=0, x2=1, y2=1, three_points=[[0, 0], [10, 0], [5, 5]])


# ---------------------------------------------------------------- proyectar vértices
def test_proyectar_vertices_del_modelo():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=10, name="Caja")
    ok(s, "create_sketch", plane="XY", name="Plano")
    r = ok(s, "project_to_sketch", vertices=[[10, 10, 10]], body="Caja")
    assert r["points"] and r["mode"] == "project"
    falla(s, "project_to_sketch", vertices=[[1, 2, 3]], body="Caja", esperado="ELEMENT_NOT_FOUND")
    falla(s, "project_to_sketch", vertices=[[1, 2]], body="Caja")
    falla(s, "project_to_sketch")
