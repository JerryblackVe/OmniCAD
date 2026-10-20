# -*- coding: utf-8 -*-
"""Opciones nuevas de sweep, loft y los patrones (ola 7 de B-80, MCP-58, MCP-59 y MCP-61): ruta de aristas de un cuerpo,
distancia parcial, carril guía, cara como perfil, secciones con vértices, línea central, direcciones y ejes de patrón por
aristas, distribución por extensión, simetría, copias suprimidas, puntos asociativos y espejo con una cara plana."""
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


def cuerpos(s):
    return ok(s, "get_scene_info")["bodies"]


def cuerpo(s, nombre):
    return next(c for c in cuerpos(s) if c["name"] == nombre)


def centro(c, i):
    return (c["bounding_box"]["min"][i] + c["bounding_box"]["max"][i]) / 2


def barrido_base():
    """Perfil circular r = 2 en XY y una ruta recta de 20 mm hacia +Z (boceto sobre XZ)."""
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="Perfil")
    ok(s, "draw_circle", radius=2)
    ok(s, "create_sketch", plane="XZ", name="Ruta")
    ok(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=20)
    return s


# ---------------------------------------------------------------- MCP-58: sweep
def test_barrido_con_distancia_parcial_y_con_aristas_de_un_cuerpo_como_ruta():
    s = barrido_base()
    ok(s, "sweep", sketch="Perfil", path_sketch="Ruta")
    assert cuerpos(s)[0]["volume"] == pytest.approx(math.pi * 4 * 20, rel=1e-4)
    s = barrido_base()
    ok(s, "sweep", sketch="Perfil", path_sketch="Ruta", path_distance=0.5)
    assert cuerpos(s)[0]["volume"] == pytest.approx(math.pi * 4 * 10, rel=1e-4)
    falla(s, "sweep", sketch="Perfil", path_sketch="Ruta", path_distance=0)
    falla(s, "sweep", sketch="Perfil", path_sketch="Ruta", path_distance=1.5)
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")                     # arista vertical en (10, 10)
    ok(s, "create_sketch", plane="XY", name="Perfil")
    ok(s, "draw_circle", radius=2, center_x=10, center_y=10)
    ok(s, "sweep", sketch="Perfil", path_edges="edges:|Z and >X and >Y", body="Caja")
    nuevo = next(c for c in cuerpos(s) if c["name"] != "Caja")
    assert nuevo["volume"] == pytest.approx(math.pi * 4 * 20, rel=1e-4)
    falla(s, "sweep", sketch="Perfil")
    falla(s, "sweep", path_sketch="Perfil")
    falla(s, "sweep", sketch="Perfil", path_sketch="Perfil", path_edges="edges:|Z")


def test_barrido_de_una_cara_plana_y_con_carril_guia():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")
    ok(s, "create_sketch", plane="XZ", name="Ruta")
    ok(s, "draw_line", start_x=0, start_y=20, end_x=0, end_y=30)                          # sube 10 mm sobre la tapa
    ok(s, "sweep", faces=">Z", path_sketch="Ruta", body="Caja")
    nuevo = next(c for c in cuerpos(s) if c["name"] != "Caja")
    assert nuevo["volume"] == pytest.approx(400 * 10, rel=1e-4)
    s = barrido_base()
    ok(s, "create_sketch", plane="XZ", name="Carril")
    ok(s, "draw_line", start_x=2, start_y=0, end_x=2, end_y=20)
    ok(s, "sweep", sketch="Perfil", path_sketch="Ruta", rail_sketch="Carril", rail_scale="none")
    assert cuerpos(s)[0]["volume"] == pytest.approx(math.pi * 4 * 20, rel=1e-2)
    falla(s, "sweep", sketch="Perfil", path_sketch="Ruta", rail_sketch="Ruta", rail_curves=[99], esperado="ENTITY_NOT_FOUND")


# ---------------------------------------------------------------- MCP-59: loft
def test_solevacion_hasta_un_vertice_con_linea_central_y_con_carriles():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, x=100, name="Caja")                # vértice en (110, 10, 20)
    ok(s, "create_sketch", plane="XY", name="Base")
    ok(s, "draw_circle", radius=5, center_x=110, center_y=10)
    ok(s, "loft", sections=[{"sketch": "Base", "profile": 0}, [110, 10, 20]], body="Caja")
    cono = next(c for c in cuerpos(s) if c["name"] != "Caja")
    assert cono["volume"] == pytest.approx(math.pi * 25 * 20 / 3, rel=1e-3)               # un cono: termina en punta
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="A")
    ok(s, "draw_circle", radius=5)
    ok(s, "create_construction_plane", plane="XY", offset=20, name="Alto")
    ok(s, "create_sketch", plane="Alto", name="B")
    ok(s, "draw_circle", radius=5)
    ok(s, "create_sketch", plane="XZ", name="Centro")
    centro_id = ok(s, "draw_line", start_x=0, start_y=0, end_x=0, end_y=20)["entities"][0]["id"]
    ok(s, "loft", sketches=["A", "B"], center_line=[{"sketch": "Centro", "curve": centro_id}])
    assert cuerpos(s)[0]["volume"] == pytest.approx(math.pi * 25 * 20, rel=1e-3)
    falla(s, "loft", sketches=["A", "B"], rails=[{"sketch": "Centro", "curve": centro_id}],
          center_line=[{"sketch": "Centro", "curve": centro_id}])
    falla(s, "loft", sketches=["A", "B"], sections=["A", "B"])
    falla(s, "loft")
    falla(s, "loft", sections=[{"sketch": "A"}])


# ---------------------------------------------------------------- MCP-61: patrones
def dos_cajas():
    s = api.Sesion()
    ok(s, "create_box", length=5, width=5, height=5, x=0, name="Pieza")
    ok(s, "create_box", length=20, width=20, height=20, x=200, name="Guia")                # aristas a 190..210
    return s


def test_patron_rectangular_con_arista_como_direccion_extension_simetria_y_supresion():
    s = dos_cajas()
    ok(s, "rectangular_pattern", bodies="Pieza", x_count=3, x_spacing=10, axis1="edges:|Y and <Z and <X", body="Guia")
    copias = [c for c in cuerpos(s) if c["name"].startswith("Pieza")]
    assert len(copias) == 3
    ys = sorted(centro(c, 1) for c in copias)
    assert ys[2] - ys[0] == pytest.approx(20) and all(abs(centro(c, 0)) < 1e-6 for c in copias)   # a lo largo de Y
    s = dos_cajas()
    ok(s, "rectangular_pattern", bodies="Pieza", x_count=3, x_spacing=40, distribution="extent")
    xs = sorted(centro(c, 0) for c in cuerpos(s) if c["name"].startswith("Pieza"))
    assert xs[-1] - xs[0] == pytest.approx(40)                                         # 40 = distancia TOTAL
    s = dos_cajas()
    ok(s, "rectangular_pattern", bodies="Pieza", x_count=3, x_spacing=10, symmetric=True)
    xs = sorted(centro(c, 0) for c in cuerpos(s) if c["name"].startswith("Pieza"))
    assert len(xs) == 5 and xs[-1] - xs[0] == pytest.approx(40)
    s = dos_cajas()
    ok(s, "rectangular_pattern", bodies="Pieza", x_count=4, x_spacing=10, suppress=[1, 2])
    xs = sorted(centro(c, 0) for c in cuerpos(s) if c["name"].startswith("Pieza"))
    assert len(xs) == 2 and xs[1] - xs[0] == pytest.approx(30)                         # quedan el original y la copia 3
    falla(s, "rectangular_pattern", bodies="Pieza", x_count=4, x_spacing=10, suppress=[4])
    falla(s, "rectangular_pattern", bodies="Pieza", x_count=4, x_spacing=10, suppress=[0])
    falla(s, "rectangular_pattern", bodies="Pieza", x_count=2, axis1="no_existe")


def test_patron_circular_por_angulo_entre_copias_y_con_copias_suprimidas():
    s = api.Sesion()
    ok(s, "create_box", length=5, width=5, height=5, x=20, name="Pieza")
    ok(s, "circular_pattern", count=3, bodies="Pieza", total_angle=30, distribution="spacing")
    copias = [c for c in cuerpos(s) if c["name"].startswith("Pieza")]
    angulos = sorted(round(math.degrees(math.atan2(centro(c, 1), centro(c, 0)))) for c in copias)
    assert angulos == [0, 30, 60]                                                       # 30° ENTRE copias
    s = api.Sesion()
    ok(s, "create_box", length=5, width=5, height=5, x=20, name="Pieza")
    ok(s, "circular_pattern", count=4, bodies="Pieza", suppress=[1, 3])
    assert len([c for c in cuerpos(s) if c["name"].startswith("Pieza")]) == 2
    s = dos_cajas()
    ok(s, "create_construction_axis", type="arista", references=["edges:|Z and >X and >Y"], body="Guia", name="Eje1")
    ok(s, "circular_pattern", count=3, bodies="Pieza", axis="Eje1", total_angle=180)
    assert len([c for c in cuerpos(s) if c["name"].startswith("Pieza")]) == 3


def test_patron_en_ruta_de_aristas_y_en_puntos_asociativos():
    s = dos_cajas()
    ok(s, "path_pattern", bodies="Pieza", count=3, distance=20, path_edges="edges:|Y and <Z and <X", body="Guia")
    copias = [c for c in cuerpos(s) if c["name"].startswith("Pieza")]
    assert len(copias) == 3
    assert max(centro(c, 1) for c in copias) - min(centro(c, 1) for c in copias) == pytest.approx(20, abs=1e-3)
    falla(s, "path_pattern", bodies="Pieza", count=3, distance=20)
    falla(s, "path_pattern", bodies="Pieza", path_edges="edges:|Y", body="Guia")
    s = dos_cajas()
    ok(s, "point_pattern", bodies="Pieza", point_refs=[[190, -10, 0], [210, 10, 20]])
    copias = [c for c in cuerpos(s) if c["name"].startswith("Pieza")]
    assert len(copias) == 3                                                             # el original y una copia por vértice
    ok(s, "undo")
    ok(s, "point_pattern", bodies="Pieza", point_refs=[[190, -10, 0]], reference_point=[190, -10, 0])
    falla(s, "point_pattern", bodies="Pieza", point_refs=[[1, 2, 3]], esperado="ELEMENT_NOT_FOUND")
    falla(s, "point_pattern", bodies="Pieza", point_refs=[[190, -10, 0]], reference=[0, 0, 0],
          reference_point=[190, -10, 0])


def test_multitransformacion_con_espejo_de_una_cara_plana():
    s = dos_cajas()
    ok(s, "multi_transform", bodies="Pieza", transforms=[{"type": "mirror", "plane": ">X", "body": "Guia"}])
    copias = [c for c in cuerpos(s) if c["name"].startswith("Pieza")]
    assert len(copias) == 2
    assert sorted(centro(c, 0) for c in copias) == pytest.approx([0, 2 * 210 - 0])
    s = dos_cajas()
    ok(s, "multi_transform", bodies="Pieza", transforms=[
        {"type": "rectangular", "axis": "edges:|Y and <Z and <X", "count": 2, "spacing": 10, "body": "Guia"}])
    assert len([c for c in cuerpos(s) if c["name"].startswith("Pieza")]) == 2
