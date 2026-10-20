# -*- coding: utf-8 -*-
"""Opciones nuevas de herramientas de modificar (ola 7 de B-80): agujero en vértices y con ángulo de punta (MCP-60),
empalme de reglas, variable y de cuerda (MCP-63), chaflán de dos distancias y de distancia y ángulo (MCP-64), vaciado con
espesor exterior (MCP-65), desmoldeo de dos lados (MCP-66), desfase de aristas en un plano de construcción (MCP-67) y
quitar empalmes de varios cuerpos (MCP-69). Volúmenes exactos sobre cajas de 20 mm."""
import math

import pytest

from omnicad import api

L = 20.0
V = L ** 3


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, esperado="INVALID_ARGUMENTS", **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == esperado, r
    return r


def volumen(s, nombre=None):
    cuerpos = ok(s, "get_scene_info")["bodies"]
    return next(c["volume"] for c in cuerpos if nombre is None or c["name"] == nombre)


def caja(nombre="Caja", z=0):
    s = api.Sesion()
    ok(s, "create_box", length=L, width=L, height=L, z=z, name=nombre)
    return s


ARISTA = "edges:|Z and >X and >Y"          # una arista vertical de 20 mm


# ---------------------------------------------------------------- MCP-64: chaflán
def test_chaflan_de_dos_distancias_y_de_distancia_y_angulo():
    s = caja()
    ok(s, "chamfer", edges=ARISTA, distance=2, type="two_distances", distance2=3)
    assert volumen(s) == pytest.approx(V - 2 * 3 / 2 * L)
    s = caja()
    ok(s, "chamfer", edges=ARISTA, distance=3, type="distance_angle", angle=30)
    assert volumen(s) == pytest.approx(V - 3 * 3 * math.tan(math.radians(30)) / 2 * L, rel=1e-6)
    s = caja()
    ok(s, "chamfer", edges=ARISTA, distance=2, type="two_distances", distance2=3, flip=True)
    assert volumen(s) == pytest.approx(V - 2 * 3 / 2 * L)                  # voltear no cambia el volumen quitado
    falla(s, "chamfer", edges=ARISTA, distance=2, type="two_distances")
    falla(s, "chamfer", edges=ARISTA, distance=2, type="distance_angle")
    falla(s, "chamfer", edges=ARISTA, distance=2, type="distance_angle", angle=95)
    s = caja()                                                             # sin cadena tangente: solo la arista elegida
    ok(s, "chamfer", edges=ARISTA, distance=1, tangent_chain=False)
    assert volumen(s) == pytest.approx(V - 0.5 * L)


# ---------------------------------------------------------------- MCP-63: empalme
def test_empalme_de_cuerda_variable_y_de_reglas():
    s = caja()
    ok(s, "fillet", edges=ARISTA, radius=2)
    constante = V - volumen(s)
    assert constante == pytest.approx((1 - math.pi / 4) * 4 * L, abs=1e-3)
    s = caja()
    ok(s, "fillet", edges=ARISTA, radius_type="chord", chord_length=2 * math.sqrt(2))      # cuerda = r√2 → r = 2
    assert V - volumen(s) == pytest.approx(constante, rel=1e-3)
    s = caja()
    ok(s, "fillet", edges=ARISTA, radius=1, radius_type="variable", end_radius=3)
    quitado = V - volumen(s)
    chico, grande = (1 - math.pi / 4) * 1 * L, (1 - math.pi / 4) * 9 * L
    assert chico < quitado < grande
    # empalme de reglas: todas las aristas de la cara de arriba = empalmar esas 4 aristas
    s1 = caja()
    ok(s1, "fillet", faces_a=">Z", radius=1.5)
    s2 = caja()
    ok(s2, "fillet", edges="edges:%LINE and >Z[0] and |X or edges:%LINE and >Z[0] and |Y", radius=1.5) \
        if False else ok(s2, "fillet", edges=["edges:|X and >Z", "edges:|Y and >Z"], radius=1.5)
    assert volumen(s1) == pytest.approx(volumen(s2), rel=1e-6)
    s3 = caja()                                                             # «entre»: solo las aristas entre arriba y +X
    ok(s3, "fillet", faces_a=">Z", faces_b=">X", radius=1.5)
    assert V - volumen(s3) == pytest.approx((1 - math.pi / 4) * 1.5 ** 2 * L, abs=1e-3)
    falla(s3, "fillet", radius_type="chord", edges=ARISTA)
    falla(s3, "fillet", radius_type="variable", edges=ARISTA, radius=1)
    falla(s3, "fillet", edges=ARISTA, faces_a=">Z", radius=1)
    falla(s3, "fillet", edges=ARISTA)                                       # sin radio no inventa un empalme de 1 mm
    falla(s3, "fillet")


# ---------------------------------------------------------------- MCP-65: vaciado
def test_vaciado_con_espesor_exterior_y_esquinas_redondeadas():
    s = caja()
    r = ok(s, "shell", body="Caja", faces=">Z", thickness=1, direction="both", outside_thickness=2)
    c = ok(s, "get_scene_info")["bodies"][0]["bounding_box"]["size"]
    assert c[0] == pytest.approx(L + 4) and c[1] == pytest.approx(L + 4)      # crece 2 mm por lado
    assert r["faces_removed"] == 1
    s = caja()
    ok(s, "shell", body="Caja", faces=">Z", thickness=2)
    afilado = volumen(s)
    assert afilado == pytest.approx(V - (L - 4) ** 2 * (L - 2))
    s = caja()
    ok(s, "shell", body="Caja", faces=">Z", thickness=2, corners="rounded", direction="outside")
    assert volumen(s) > 0
    s = caja()
    ok(s, "fillet", edges="edges:|Z", radius=3)
    ok(s, "shell", body="Caja", faces=">Z", thickness=1, tangent_chain=False)
    assert volumen(s) > 0
    falla(s, "shell", body="Caja", faces=">Z", thickness=1, outside_thickness=-1)


# ---------------------------------------------------------------- MCP-66: desmoldeo
def test_desmoldeo_de_dos_lados_y_simetrico_con_plano_de_construccion():
    def desmoldeado(**args):
        s = api.Sesion()
        ok(s, "create_box", length=L, width=L, height=L, z=-L / 2, name="Caja")        # de z = −10 a z = 10
        r = api.llamar(s, "create_construction_plane", {"plane": "XY", "offset": 0})
        assert r["ok"], r
        ok(s, "draft", faces="faces:#Z", angle=5, neutral="Plano1", **args)
        return volumen(s)
    simetrico = desmoldeado(sides="symmetric")
    dos = desmoldeado(sides="two", angle2=5)
    assert simetrico == pytest.approx(dos, rel=1e-9) and simetrico < V
    assert desmoldeado(sides="one") != pytest.approx(simetrico, rel=1e-6)
    s = caja()
    falla(s, "draft", faces="faces:#Z", angle=5, sides="two")
    falla(s, "draft", faces="faces:#Z", angle=5, neutral="NoExiste", esperado="PLANE_NOT_FOUND")


# ---------------------------------------------------------------- MCP-67: desfase en un plano de construcción
def test_desfase_de_aristas_sobre_un_plano_de_construccion():
    s = caja()
    ok(s, "create_construction_plane", plane="XY", offset=5, name="Alto")
    r = ok(s, "offset_edges", distance=2, edges=["edges:|X and >Z and >Y"], plane="Alto")
    marco = ok(s, "get_sketch", sketch=r["sketch"]["id"])["plane_frame"]
    assert marco["origin"][2] == pytest.approx(5)                                  # el boceto quedó en el plano elegido
    falla(s, "offset_edges", distance=2, edges=["edges:|X and >Z and >Y"], plane="NoExiste", esperado="INVALID_SELECTOR")


# ---------------------------------------------------------------- MCP-69: quitar empalmes de varios cuerpos
def test_quitar_empalmes_de_varios_cuerpos():
    s = api.Sesion()
    ok(s, "create_box", length=L, width=L, height=L, x=0, name="A")
    ok(s, "create_box", length=L, width=L, height=L, x=50, name="B")
    ok(s, "fillet", edges="edges:|Z", radius=2, body="A")
    ok(s, "fillet", edges="edges:|Z", radius=2, body="B")
    assert volumen(s, "A") < V and volumen(s, "B") < V
    r = ok(s, "remove_fillets", body=["A", "B"], max_radius=3)
    assert sorted(r["bodies_affected"]) == sorted(c["id"] for c in ok(s, "get_scene_info")["bodies"])
    assert volumen(s, "A") == pytest.approx(V) and volumen(s, "B") == pytest.approx(V)
    falla(s, "remove_fillets", body=[], max_radius=3)
    ok(s, "undo")
    assert volumen(s, "A") < V and volumen(s, "B") < V                              # un solo deshacer para los dos
    s2 = caja()
    ok(s2, "fillet", edges="edges:|Z", radius=2)
    ok(s2, "remove_fillets", body="Caja", max_radius=3)                              # el texto suelto sigue valiendo
    assert volumen(s2) == pytest.approx(V)


# ---------------------------------------------------------------- MCP-60: agujeros
def test_agujero_en_un_vertice_con_angulo_de_punta_flip_y_varios_cuerpos():
    s = caja()
    ok(s, "create_hole", diameter=4, depth=5, positions=[[10, 10, 20]])
    assert V - volumen(s) == pytest.approx(math.pi * 2 ** 2 * 5 / 4, rel=1e-4)       # un cuarto de cilindro (la esquina)
    plano = caja()
    ok(plano, "create_hole", diameter=4, depth=5, positions=[[10, 10, 20]], drill_tip=True, tip_angle=90)
    punta118 = caja()
    ok(punta118, "create_hole", diameter=4, depth=5, positions=[[10, 10, 20]], drill_tip=True)
    cono = lambda ang: math.pi * 2 ** 2 * (2 / math.tan(math.radians(ang / 2))) / 3 / 4        # noqa: E731
    assert volumen(punta118) - volumen(plano) == pytest.approx(cono(90) - cono(118), rel=1e-3)
    s2 = caja()
    r = api.llamar(s2, "create_hole", {"diameter": 4, "depth": 5, "positions": [[10, 10, 20]], "flip": True})
    assert (not r["ok"]) or volumen(s2) == pytest.approx(V)                          # hacia arriba: no corta nada
    s3 = api.Sesion()
    ok(s3, "create_box", length=L, width=L, height=L, name="Abajo")
    ok(s3, "create_box", length=L, width=L, height=L, z=L, name="Arriba")
    ok(s3, "create_hole", diameter=4, face=">Z", body="Arriba", through_all=True, points=[[0, 0, 40]], bodies=["Abajo"])
    assert V - volumen(s3, "Arriba") == pytest.approx(math.pi * 4 * L, rel=1e-4)
    assert V - volumen(s3, "Abajo") == pytest.approx(math.pi * 4 * L, rel=1e-4)      # el mismo agujero atravesó los dos
    falla(s, "create_hole", diameter=4, depth=5, positions=[[1, 2, 3]], esperado="ELEMENT_NOT_FOUND")
    falla(s, "create_hole", diameter=4, depth=5, positions=[[10, 10, 20]], face=">Z", points=[[0, 0]])
