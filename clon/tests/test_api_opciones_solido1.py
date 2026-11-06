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


def test_dos_lados_con_distancia_negativa_da_lo_mismo_con_y_sin_conicidad():
    """B-205: en «Dos lados» cada distancia es una magnitud hacia su lado (Fusion: “a unique extrusion on each
    side of the profile plane”); el signo no pasa el lado a la otra margen. Antes el camino rápido perdía el
    lado 2 en la unión (2000 mm³) y el del kernel lo conservaba (3000 mm³)."""
    def medir(distance, distance2, **args):
        s = api.Sesion()
        rect(s)
        ok(s, "extrude", sketch="B", distance=distance, direction="two_sides", distance2=distance2, **args)
        c = cuerpo(s)
        return c["volume"], c["bounding_box"]["min"][2], c["bounding_box"]["max"][2]

    for d1, d2 in ((10, -5), (-10, 5)):
        recto = medir(d1, d2)
        assert recto == pytest.approx((3000, -5, 10), abs=1e-6)         # 20·10·(10+5): los dos lados presentes
        inclinado = medir(d1, d2, taper_angle=0.001)                    # misma receta con un poco de conicidad
        assert inclinado[1:] == pytest.approx(recto[1:], abs=1e-6)
        assert inclinado[0] == pytest.approx(recto[0], rel=1e-3)
    from omnicad.nucleo import geometria as geo
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="L")
    ok(s, "draw_line", sketch="L", start_x=0, start_y=0, end_x=20, end_y=0)
    curva = next(iter(s.doc.estado_final.bocetos[s.paso("L").id].boceto.curvas))
    cid = ok(s, "create_surface_extrude", profiles={"sketch": "L", "curve": curva},
             sides="two_sides", distance=10, distance2=-5)["bodies_created"][0]["id"]
    lo, hi = geo.caja_envolvente(s.cuerpo(cid).forma)
    assert (lo[2], hi[2]) == pytest.approx((-5, 10), abs=1e-6)          # la superficie, con la misma regla


def test_inicio_objeto_en_un_plano_inclinado_arranca_sobre_el():
    """B-206 · Inicio › Objeto con un plano inclinado (Fusion: “Starts extrusion from a face or plane that you
    select”): la base del cuerpo queda sobre ese plano. Antes se usaba solo su altura y el cuerpo salía igual
    que sin Inicio, sin avisar."""
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from omnicad.nucleo import geometria as geo
    t30 = math.tan(math.radians(30))

    def desvio_de_la_base(forma):
        """El mayor desvío de los vértices de abajo respecto del plano z = y·tan30° (el plano de inicio)."""
        puntos = (BRep_Tool.Pnt_s(TopoDS.Vertex(v)) for v in geo._explorar(forma, TopAbs_VERTEX))
        return max(abs(p.Z() - p.Y() * t30) for p in puntos if p.Z() - p.Y() * t30 < 5)   # los de la tapa, a +10

    s = api.Sesion()
    rect(s)
    ok(s, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="PInc")
    cid = ok(s, "extrude", sketch="B", distance=10, start="object", start_object="PInc")["bodies_created"][0]["id"]
    assert desvio_de_la_base(s.cuerpo(cid).forma) < 1e-6
    assert cuerpo(s)["bounding_box"]["max"][2] == pytest.approx(10 + 10 * t30, abs=1e-3)   # la caja viene redondeada
    assert cuerpo(s)["volume"] == pytest.approx(2000, rel=1e-6)         # 20·10 de perfil, 10 mm a lo largo de Z
    # delgada cerrada: la pared se mide en el plano del perfil (1 mm en X y en Y) y la base queda sobre el plano
    cid = ok(s, "extrude", sketch="B", distance=10, start="object", start_object="PInc", thin=True, wall_thickness=1,
             wall_location="center", operation="new_body")["bodies_created"][0]["id"]
    assert geo.volumen_exacto(s.cuerpo(cid).forma) == pytest.approx(600, rel=1e-9)   # 60 de perímetro · 1 · 10
    lo, hi = geo.caja_envolvente(s.cuerpo(cid).forma)
    assert (lo[0], lo[1], hi[0], hi[1]) == pytest.approx((-0.5, -0.5, 20.5, 10.5), abs=1e-6)
    assert desvio_de_la_base(s.cuerpo(cid).forma) < 1e-6
    # «Al objeto» paralelo: la tapa queda plana en el objeto (no a una distancia desde el centro de la base)
    ok(s, "create_construction_plane", plane="XY", offset=30, name="Tope")
    cid = ok(s, "extrude", sketch="B", start="object", start_object="PInc", extent="to_object", to="Tope",
             operation="new_body")["bodies_created"][0]["id"]
    lo, hi = geo.caja_envolvente(s.cuerpo(cid).forma)
    assert (lo[2], hi[2]) == pytest.approx((0, 30), abs=1e-6)
    assert geo.volumen_exacto(s.cuerpo(cid).forma) == pytest.approx(200 * (30 - 5 * t30), rel=1e-9)
    # «Todo» cortando: pasa de largo también desde el punto más bajo de la base inclinada
    s = api.Sesion()
    ok(s, "create_box", width=40, length=40, height=40, x=-10, y=-15, z=-5)      # x −30..10, y −35..5, z −5..35
    rect(s)
    ok(s, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="PInc")
    ok(s, "extrude", sketch="B", start="object", start_object="PInc", extent="all", operation="cut")
    quitado = 10 * 5 * 35 - 10 * 5 * 2.5 * t30                       # x 0..10, y 0..5, de la base inclinada a z=35
    assert geo.volumen_exacto(s.cuerpo(cuerpo(s)["id"]).forma) == pytest.approx(64000 - quitado, rel=1e-9)
    # con curvas: el círculo proyectado es una elipse exacta (antes, una B-spline aproximada: 788,63 mm³)
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="C")
    ok(s, "draw_circle", center_x=0, center_y=0, radius=5, sketch="C")
    ok(s, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="PInc")
    cid = ok(s, "extrude", sketch="C", distance=10, start="object", start_object="PInc")["bodies_created"][0]["id"]
    assert geo.volumen_exacto(s.cuerpo(cid).forma) == pytest.approx(250 * math.pi, rel=1e-9)
    cid = ok(s, "extrude", sketch="C", distance=10, start="object", start_object="PInc", thin=True, wall_thickness=1,
             wall_location="center", operation="new_body")["bodies_created"][0]["id"]
    assert geo.volumen_exacto(s.cuerpo(cid).forma) == pytest.approx(100 * math.pi, rel=1e-9)   # π(5,5² − 4,5²)·10
    cid = ok(s, "extrude", sketch="C", distance=10, start="object", start_object="PInc",
             taper_angle=5)["bodies_created"][0]["id"]
    assert geo.es_valida(s.cuerpo(cid).forma)
    assert geo.volumen_exacto(s.cuerpo(cid).forma) > 250 * math.pi
    s = api.Sesion()
    rect(s)
    ok(s, "create_construction_plane", plane="XY", offset=4, name="Par")
    ok(s, "extrude", sketch="B", distance=2, start="object", start_object="Par")
    assert cuerpo(s)["bounding_box"]["min"][2] == pytest.approx(4)      # paralelo: da lo mismo que antes
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="L")
    ok(s, "draw_line", sketch="L", start_x=0, start_y=0, end_x=0, end_y=10)
    ok(s, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="PInc")
    curva = next(iter(s.doc.estado_final.bocetos[s.paso("L").id].boceto.curvas))
    cid = ok(s, "create_surface_extrude", profiles={"sketch": "L", "curve": curva}, start="object",
             start_object="PInc", distance=10)["bodies_created"][0]["id"]
    lo, hi = geo.caja_envolvente(s.cuerpo(cid).forma)
    assert (lo[2], hi[2]) == pytest.approx((0.0, 10 + 10 * t30), abs=1e-6)   # lo mismo en SUPERFICIE

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
