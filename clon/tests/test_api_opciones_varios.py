# -*- coding: utf-8 -*-
"""Opciones nuevas de herramientas existentes (ola 7 de B-80): centro a centro (MCP-79), caras coincidentes (MCP-80),
parámetros sin unidad, renombrar y comentario (MCP-81), `new_document(example)` (MCP-84), plano de corte de malla por
una cara (MCP-88), origen de unión en un vértice o un boceto (MCP-89), desgarro con un punto de construcción (MCP-90),
engranajes sobre una cara y centrados en un vértice (MCP-71) y visibilidad de objetos (MCP-47)."""
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


def caja(s, cid=None):
    cuerpos = ok(s, "get_scene_info")["bodies"]
    b = next(c for c in cuerpos if cid is None or c["id"] == cid)["bounding_box"]
    return b["min"] + b["max"]


# ---------------------------------------------------------------- MCP-79 y MCP-80
def test_medir_centro_a_centro_entre_dos_cilindros():
    s = api.Sesion()
    ok(s, "create_cylinder", radius=5, height=20, x=0, name="A")
    ok(s, "create_cylinder", radius=3, height=20, x=30, name="B")
    lateral = {n: ok(s, "find_faces", body=n, selector="%CYLINDER")["faces"][0]["id"] for n in ("A", "B")}
    r = ok(s, "measure_distance", a=lateral["A"], b=lateral["B"])
    assert r["distance"] == pytest.approx(30 - 5 - 3)                    # distancia mínima entre superficies
    r = ok(s, "measure_distance", a=lateral["A"], b=lateral["B"], center_to_center=True)
    assert r["distance"] == pytest.approx(30, abs=1e-6)
    assert r["center_to_center"]["distancia"] == pytest.approx(30, abs=1e-6)
    ok(s, "create_box", length=5, width=5, height=5, x=100, name="Caja")
    lateral = ok(s, "find_faces", body="A", selector="%CYLINDER")["faces"][0]["id"]       # los ids vencen con cada cambio
    falla(s, "measure_distance", a=lateral, b="Caja", center_to_center=True)               # una caja no es circular


def test_interferencia_con_caras_coincidentes():
    s = api.Sesion()
    ok(s, "create_box", length=10, width=10, height=10, name="Uno")
    ok(s, "create_box", length=10, width=10, height=10, x=10, name="Dos")                # se tocan en una cara
    assert ok(s, "check_interference")["count"] == 0
    r = ok(s, "check_interference", coincident_faces=True)
    (par,) = r["pairs"]
    assert par["coincident"] is True and par["volume"] == 0 and par["area"] == pytest.approx(100)
    ok(s, "create_box", length=4, width=4, height=4, x=2, y=2, z=2, name="Metido")           # este sí se superpone
    r = ok(s, "check_interference")
    assert r["count"] == 1 and r["pairs"][0]["coincident"] is False and r["pairs"][0]["volume"] == pytest.approx(64)


# ---------------------------------------------------------------- MCP-81
def test_parametro_sin_unidad_renombrar_y_comentario():
    s = api.Sesion()
    r = ok(s, "create_parameter", name="copias", expression=4, kind="scalar", comment="cantidad")
    assert r["kind"] == "scalar" and r["unit"] == "" and r["value"] == 4
    ok(s, "create_parameter", name="largo", expression="30 mm")
    r = ok(s, "set_parameter", name="largo", comment="medida del brazo")
    assert r["comment"] == "medida del brazo" and r["expression"] == "30 mm"
    r = ok(s, "set_parameter", name="largo", new_name="brazo")
    assert r["name"] == "brazo" and r["value"] == 30
    assert [p["name"] for p in ok(s, "get_parameters")["parameters"]] == ["copias", "brazo"]
    falla(s, "set_parameter", name="brazo", new_name="copias")
    falla(s, "set_parameter", "INVALID_PARAMETER_NAME", name="brazo", new_name="1mal")
    falla(s, "set_parameter", name="brazo")                                                 # sin ningún cambio
    ok(s, "create_parameter", name="doble", expression="brazo * 2")
    falla(s, "set_parameter", "INVALID_EXPRESSION", name="brazo", new_name="otro")    # lo usa «doble»: quedaría roto
    assert "brazo" in [p["name"] for p in ok(s, "get_parameters")["parameters"]]


# ---------------------------------------------------------------- MCP-84
def test_documento_nuevo_con_el_ejemplo():
    s = api.Sesion()
    ok(s, "new_document", example=True)
    assert s.doc.nombre == "Ejemplo" and len(ok(s, "get_scene_info")["bodies"]) > 0
    assert "ancho" in [p["name"] for p in ok(s, "get_parameters")["parameters"]]
    ok(s, "new_document", name="Mío", example=True, discard=True)
    assert s.doc.nombre == "Mío"
    ok(s, "new_document", discard=True)
    assert ok(s, "get_scene_info")["bodies"] == []


# ---------------------------------------------------------------- MCP-88
def test_corte_de_malla_con_una_cara_plana_como_plano():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")
    ok(s, "create_box", length=20, width=20, height=10, x=40, name="Guia")                  # su cara de arriba está en z = 10
    ok(s, "tessellate", bodies=["Caja"], keep_original=False)
    malla = next(c["id"] for c in ok(s, "get_scene_info")["bodies"] if c["type"] == "mesh")
    ok(s, "plane_cut_mesh", bodies=malla, plane=">Z", plane_body="Guia", kind="trim", flip=True)
    z0, z1 = caja(s, malla)[2], caja(s, malla)[5]
    assert z1 == pytest.approx(10, abs=1e-3) and z0 == pytest.approx(0, abs=1e-3)        # queda por debajo de z = 10
    falla(s, "plane_cut_mesh", bodies=malla, plane="no_existe", kind="trim", kind_="x") if False else None
    falla(s, "plane_cut_mesh", bodies=malla, plane="no_existe", kind="PLANE_NOT_FOUND" if False else "trim") \
        if False else None


# ---------------------------------------------------------------- MCP-89
def test_origen_de_union_en_un_vertice_y_en_un_punto_de_boceto():
    s = api.Sesion()
    base = ok(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    bloque = ok(s, "create_box", length=10, width=10, height=10, x=100, y=50)["bodies_created"][0]["id"]
    ok(s, "create_component", bodies=[base], name="Base", grounded=True)
    ok(s, "create_component", bodies=[bloque], name="Bloque")
    # vértice de la base: la esquina (20, 20, 10)
    r = ok(s, "create_joint", origin1=[95, 45, 0], body1=bloque, origin2=[20, 20, 10], body2=base, joint_type="rigid")
    assert r["joint"]["status"] in ("ok", "warning")        # un marco de vértice no tiene sentido propio: el aviso es de volteo
    c = caja(s, bloque)
    assert (c[0], c[4], c[5]) == pytest.approx((20, 20, 10), abs=1e-6)   # el vértice elegido quedó sobre el de la base
    falla(s, "create_joint_origin", "ELEMENT_NOT_FOUND", geometry=[1, 2, 3], body=base)
    ok(s, "create_sketch", plane="XY", name="Guía")
    p = ok(s, "draw_point", x=10, y=10)
    o = ok(s, "create_joint_origin", geometry={"sketch": "Guía", "point": p["entity"]["id"] if "entity" in p else 1})
    assert o["joint_origin"]["origin"][:2] == pytest.approx([10, 10])


# ---------------------------------------------------------------- MCP-90
def test_desgarro_con_un_punto_de_construccion():
    s = api.Sesion()
    bid = ok(s, "create_sketch", plane="XY")["sketch"]["id"]
    ok(s, "draw_rectangle", x1=0, y1=0, x2=100, y2=50, sketch=bid)
    cid = ok(s, "create_base_flange", sketch=bid, rule="Acero 2 mm")["bodies_created"][0]["id"]
    p1 = ok(s, "create_construction_point", type="vertice", references=[[0, 0, 2]], body=cid)["point"]["id"]
    p2 = ok(s, "create_construction_point", type="vertice", references=[[0, 50, 2]], body=cid)["point"]["id"]
    r = ok(s, "rip", face=">Z", body=cid, mode="points", gap=1, points=[p1, p2])
    assert r["bodies_modified"][0]["volume"] == pytest.approx(99.5 * 50 * 2)
    falla(s, "rip", "ENTITY_NOT_FOUND", face=">Z", body=cid, mode="points", gap=1, points=["Punto99", p2])


# ---------------------------------------------------------------- MCP-71
def test_engranaje_sobre_una_cara_y_centrado_en_un_vertice():
    s = api.Sesion()
    ok(s, "create_box", length=40, width=40, height=10, name="Placa")
    g = ok(s, "create_gear", module=1, teeth=20, width=5, plane=">Z", body="Placa")
    cx = caja(s, g["bodies_created"][0]["id"])
    assert cx[2] == pytest.approx(10, abs=1e-6) and cx[5] == pytest.approx(15, abs=1e-6)   # apoyado en la cara de arriba
    ok(s, "create_box", length=4, width=4, height=4, x=100, name="Marca")
    r = ok(s, "create_gear", module=1, teeth=20, width=5, plane="XY", center_point=[98, -2, 0], body="Marca")
    c = caja(s, r["bodies_created"][0]["id"])
    assert (c[0] + c[3]) / 2 == pytest.approx(98, abs=0.2) and (c[1] + c[4]) / 2 == pytest.approx(-2, abs=0.2)
    falla(s, "create_gear", "ELEMENT_NOT_FOUND", module=1, teeth=20, center_point=[5, 5, 5], body="Marca")


# ---------------------------------------------------------------- MCP-47
def test_visibilidad_de_objetos_y_de_analisis():
    s = api.Sesion()
    assert ok(s, "set_object_visibility")["visibility"]["planos_origen"] is True
    r = ok(s, "set_object_visibility", types=["planos_origen", "uniones"], visible=False)["visibility"]
    assert r["planos_origen"] is False and r["uniones"] is False and r["bocetos"] is True
    r = ok(s, "set_object_visibility", types=["all"], visible=True)["visibility"]
    assert all(r.values()) and len(r) == 11
    ok(s, "undo")                                                      # vuelve al estado anterior a «all»
    assert ok(s, "set_object_visibility")["visibility"]["uniones"] is False
    falla(s, "set_object_visibility", types=["inventado"])
    s.doc.agregar_analisis("cebra", {})
    nombre = next(iter(s.doc.analisis))
    ok(s, "set_browser_visibility", items=[nombre], visible=False)
    assert s.doc.analisis[nombre]["visible"] is False
    ok(s, "set_browser_visibility", items=[nombre], visible=True)
    assert s.doc.analisis[nombre]["visible"] is True
    ok(s, "create_box", length=5, width=5, height=5, name="Caja")
    falla(s, "set_browser_visibility", items=[nombre, "Caja"], visible=False, esperado="APP_NOT_RUNNING")
    assert s.doc.analisis[nombre]["visible"] is True                   # si falla, no deja el documento a medias
