# -*- coding: utf-8 -*-
"""Opciones nuevas de extrude, revolve, mirror y move_body (ola 7 de B-80, MCP-56, MCP-57, MCP-62 y MCP-68):
extrusión delgada, inicio en desfase u objeto, media longitud, hasta un objeto o todo, conicidad del lado 2, caras como
perfil, curvas abiertas, ejes de revolución de otro boceto, espejo con una cara plana y los tipos de movimiento.
Volúmenes y cajas exactos."""
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


def cuerpo(s, nombre=None):
    cs = ok(s, "get_scene_info")["bodies"]
    return next(c for c in cs if nombre is None or c["name"] == nombre)


def rect(s, plano="XY", nombre="B", x1=0, y1=0, x2=20, y2=10):
    ok(s, "create_sketch", plane=plano, name=nombre)
    ok(s, "draw_rectangle", x1=x1, y1=y1, x2=x2, y2=y2, sketch=nombre)


# ---------------------------------------------------------------- MCP-56: extrude
def test_extrusion_delgada_con_la_pared_a_cada_lado_y_al_centro():
    volumenes = {}
    for lugar in ("side1", "side2", "center"):
        s = api.Sesion()
        rect(s)
        ok(s, "extrude", sketch="B", distance=5, thin=True, wall_thickness=1, wall_location=lugar)
        volumenes[lugar] = cuerpo(s)["volume"]
    assert sorted((volumenes["side1"], volumenes["side2"])) == pytest.approx([280, 320])    # hacia adentro / hacia afuera
    assert volumenes["center"] == pytest.approx(300)
    s = api.Sesion()
    rect(s)
    falla(s, "extrude", sketch="B", thin=True, wall_thickness=0)
    falla(s, "extrude", sketch="B", open_curves=[1])                                        # sin thin


def test_extrusion_delgada_de_una_curva_abierta():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="B")
    linea = ok(s, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    ok(s, "extrude", sketch="B", open_curves=[linea], thin=True, wall_thickness=1, distance=5, wall_location="center")
    assert cuerpo(s)["volume"] == pytest.approx(10 * 1 * 5)
    falla(s, "extrude", sketch="B", open_curves=[99], thin=True, esperado="ENTITY_NOT_FOUND")
    falla(s, "extrude", faces=">Z", open_curves=[linea], thin=True)                  # sin sketch no hay de dónde sacar la curva


def test_extrusion_con_inicio_en_desfase_en_un_plano_y_media_longitud():
    s = api.Sesion()
    rect(s)
    ok(s, "extrude", sketch="B", distance=5, start="offset", start_offset=3)
    assert cuerpo(s)["bounding_box"]["min"][2] == pytest.approx(3) and cuerpo(s)["bounding_box"]["max"][2] == pytest.approx(8)
    s = api.Sesion()
    rect(s)
    ok(s, "create_construction_plane", plane="XY", offset=4)
    ok(s, "extrude", sketch="B", distance=2, start="object", start_object="Plano1")
    assert cuerpo(s)["bounding_box"]["min"][2] == pytest.approx(4)
    falla(s, "extrude", sketch="B", start="object")
    s = api.Sesion()
    rect(s)
    ok(s, "extrude", sketch="B", distance=5, direction="symmetric", symmetric_measure="total")
    assert cuerpo(s)["bounding_box"]["size"][2] == pytest.approx(5)
    s = api.Sesion()
    rect(s)
    ok(s, "extrude", sketch="B", distance=5, direction="symmetric", symmetric_measure="half")
    assert cuerpo(s)["bounding_box"]["size"][2] == pytest.approx(10)


def test_extrusion_hasta_un_objeto_y_atravesando_todo():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="B")
    ok(s, "draw_circle", radius=3, center_x=50)
    ok(s, "create_construction_plane", plane="XY", offset=7, name="Tope")
    ok(s, "extrude", sketch="B", extent="to_object", to="Tope")
    assert cuerpo(s)["bounding_box"]["size"][2] == pytest.approx(7)
    ok(s, "extrude", sketch="B", extent="to_object", to="Tope", to_offset=3, operation="new_body")
    assert max(c["bounding_box"]["size"][2] for c in ok(s, "get_scene_info")["bodies"]) == pytest.approx(10)
    falla(s, "extrude", sketch="B", extent="to_object")
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")
    ok(s, "create_construction_plane", plane="XY", offset=20, name="Arriba")
    ok(s, "create_sketch", plane="Arriba", name="Hueco")
    ok(s, "draw_circle", radius=3)
    ok(s, "extrude", sketch="Hueco", operation="cut", extent="all")
    assert cuerpo(s, "Caja")["volume"] == pytest.approx(20 ** 3 - math.pi * 9 * 20, abs=1e-2)


def test_conicidad_del_lado_dos_caras_como_perfil():
    def volumen(**args):
        s = api.Sesion()
        rect(s, x1=0, y1=0, x2=10, y2=10)
        ok(s, "extrude", sketch="B", distance=5, direction="two_sides", distance2=5, **args)
        return cuerpo(s)["volume"]
    recto = volumen()
    assert recto == pytest.approx(1000)
    tronco = lambda a: 5 / 3 * (100 + a * a + 10 * a)                                  # noqa: E731
    lado2 = 10 + 2 * 5 * math.tan(math.radians(10))
    esperados = (500 + tronco(lado2), 500 + tronco(10 - 2 * 5 * math.tan(math.radians(10))))
    assert any(volumen(taper_angle2=10) == pytest.approx(e, rel=1e-4) for e in esperados)
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")
    ok(s, "extrude", faces=">Z", operation="join", distance=5, body="Caja")
    assert cuerpo(s)["bounding_box"]["max"][2] == pytest.approx(25)
    assert cuerpo(s)["volume"] == pytest.approx(20 ** 3 + 400 * 5)
    falla(s, "extrude")


# ---------------------------------------------------------------- MCP-57: revolve
def test_revolucion_alrededor_de_una_linea_de_otro_boceto():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XZ", name="Eje")
    eje = ok(s, "draw_line", start_x=0, start_y=-10, end_x=0, end_y=10)["entities"][0]["id"]
    ok(s, "create_sketch", plane="XZ", name="Perfil")
    ok(s, "draw_rectangle", x1=10, y1=0, x2=15, y2=5, sketch="Perfil")
    ok(s, "revolve", sketch="Perfil", profile=0, axis={"sketch": "Eje", "curve": eje})
    assert cuerpo(s)["volume"] == pytest.approx(2 * math.pi * 12.5 * 25, rel=1e-4)       # teorema de Pappus
    s2 = api.Sesion()
    ok(s2, "create_sketch", plane="XZ", name="Perfil")
    ok(s2, "draw_rectangle", x1=10, y1=0, x2=15, y2=5, sketch="Perfil")
    falla(s2, "revolve", sketch="Perfil", profile=0, axis="no_existe", esperado="INVALID_AXIS")
    falla(s2, "revolve", sketch="Perfil", profile=0)
    falla(s2, "revolve", axis="z")


# ---------------------------------------------------------------- MCP-62: mirror
def test_espejo_con_una_cara_plana_como_plano_de_simetria():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="A")                       # cara +X en x = 10
    ok(s, "create_box", length=10, width=10, height=10, x=50, name="B")
    ok(s, "mirror", bodies="B", plane=">X", plane_body="A")
    reflejo = next(c for c in ok(s, "get_scene_info")["bodies"] if c["name"] not in ("A", "B"))
    caja = reflejo["bounding_box"]
    assert (caja["min"][0] + caja["max"][0]) / 2 == pytest.approx(2 * 10 - 50)           # 20 − 50 = −30
    falla(s, "mirror", bodies="B", plane=">X", esperado="AMBIGUOUS_REFERENCE")             # dos cuerpos: hay que decir cuál
    ok(s, "undo")
    assert len(ok(s, "get_scene_info")["bodies"]) == 2


# ---------------------------------------------------------------- MCP-68: move_body
def test_mover_por_direccion_girar_alrededor_de_un_eje_y_punto_a_punto():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, x=0, name="A")
    ok(s, "create_box", length=20, width=20, height=20, x=100, name="B")
    ok(s, "move_body", body="B", type="translate", direction="X", distance=7)
    caja = cuerpo(s, "B")["bounding_box"]
    assert (caja["min"][0] + caja["max"][0]) / 2 == pytest.approx(107)
    ok(s, "move_body", body="B", type="rotate", axis="Z", angle=90)                      # (107, 0) → (0, 107)
    caja = cuerpo(s, "B")["bounding_box"]
    assert (caja["min"][0] + caja["max"][0]) / 2 == pytest.approx(0, abs=1e-6)
    assert (caja["min"][1] + caja["max"][1]) / 2 == pytest.approx(107, abs=1e-6)
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, x=0, name="A")
    ok(s, "create_box", length=20, width=20, height=20, x=100, name="B")
    ok(s, "move_body", body="B", type="point_to_point", origin_point=[90, -10, 0], destination_point=[10, -10, 0])
    assert cuerpo(s, "B")["bounding_box"]["min"][0] == pytest.approx(10)                 # se corrió −80
    falla(s, "move_body", body="B", type="point_to_point", origin_point=[10, -10, 0])
    falla(s, "move_body", body="B", type="rotate")
    falla(s, "move_body", body="B", type="rotate", axis="Z", rotate=[0, 0, 5])
    s2 = api.Sesion()
    ok(s2, "create_box", length=20, width=20, height=20, name="A")
    ok(s2, "move_body", body="A", rotate=[0, 0, 90], translate=[5, 0, 0], pivot_point="O")  # lo de siempre sigue andando
    assert cuerpo(s2)["bounding_box"]["size"][0] == pytest.approx(20)
