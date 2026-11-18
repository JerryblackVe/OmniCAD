# -*- coding: utf-8 -*-
"""Comandos de la pestaña BOCETO que no tenían prueba propia: «Intersecar» (sk_intersecar) e «Incluir geometría 3D»
(sk_incluir_3d). Sus claves solo aparecían en la tabla de cobertura UI → API (tests/test_cobertura_ui_api.py), así que
aca se prueban por la API, con resultado numérico: radio y área del corte, largos de las aristas, coordenadas de los
vértices y vínculo con el modelo."""
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


def entidades3d(sesion):
    return llamar(sesion, "get_sketch").get("entities_3d") or []


def test_sk_intersecar_corta_el_cilindro_en_una_circunferencia(s):
    """Intersecar: el corte de un cilindro con el plano del boceto es una circunferencia de radio 5."""
    llamar(s, "create_cylinder", radius=5, height=20)
    llamar(s, "create_construction_plane", plane="XY", offset=10, name="Medio")
    llamar(s, "create_sketch", plane="Medio", name="Corte")
    r = llamar(s, "project_to_sketch", bodies=["Cuerpo1"], mode="intersect")
    assert len(r["entities"]) == 1 and r["profiles"] == 1
    info = llamar(s, "get_sketch")
    (circulo,) = info["entities"]
    assert circulo["type"] == "circle" and circulo["radius"] == pytest.approx(5)
    assert circulo["center"] == pytest.approx([0, 0])
    (perfil,) = info["profiles"]
    assert perfil["area"] == pytest.approx(math.pi * 25, rel=1e-6)
    assert len([p for p in info["points"] if p["fixed"]]) == 1


def test_sk_intersecar_con_una_caja_da_el_rectangulo_del_corte(s):
    """Intersecar una caja: 4 líneas de 20 × 10 mm, un perfil de 200 mm² y sus 4 puntos fijos."""
    llamar(s, "create_box", length=20, width=10, height=5)
    llamar(s, "create_construction_plane", plane="XY", offset=2.5, name="Medio")
    llamar(s, "create_sketch", plane="Medio", name="Corte")
    r = llamar(s, "project_to_sketch", bodies=["Cuerpo1"], mode="intersect")
    assert len(r["entities"]) == 4 and r["profiles"] == 1
    info = llamar(s, "get_sketch")
    assert sorted(e["length"] for e in info["entities"]) == pytest.approx([10, 10, 20, 20])
    (perfil,) = info["profiles"]
    assert perfil["area"] == pytest.approx(200)
    assert perfil["bounding_box"]["min"] == pytest.approx([-10, -5])
    assert perfil["bounding_box"]["max"] == pytest.approx([10, 5])
    assert len([p for p in info["points"] if p["fixed"]]) == 4


def test_sk_incluir_3d_deja_las_aristas_con_su_largo_y_los_vertices_en_su_lugar(s):
    """Incluir geometría 3D: las aristas quedan donde están (largo 10 mm en z = 5) y los vértices, en sus coordenadas."""
    llamar(s, "create_box", length=20, width=10, height=5)
    llamar(s, "create_sketch", plane="XY", name="B")
    aristas = [e["id"] for e in llamar(s, "find_edges", selector=">Z")["edges"]][:2]
    r = llamar(s, "include_3d_geometry", edges=aristas, vertices=[[-10, -5, 0], [10, 5, 5]])
    assert len(r["entities"]) == 2 and len(r["points"]) == 2
    curvas = entidades3d(s)
    assert sorted(c["length"] for c in curvas) == pytest.approx([10, 10])
    assert all(c["start"][2] == pytest.approx(5) and c["end"][2] == pytest.approx(5) for c in curvas)
    puntos = {p["id"]: p for p in llamar(s, "get_sketch")["points_3d"]}
    incluidos = [puntos[i] for i in r["points"]]
    assert sorted((p["x"], p["y"], p["z"]) for p in incluidos) == [(-10, -5, 0), (10, 5, 5)]


def test_sk_incluir_3d_toma_el_borde_de_una_cara(s):
    """Incluir geometría 3D de una cara: entran sus 4 aristas con sus largos (10, 10, 20 y 20 mm)."""
    llamar(s, "create_box", length=20, width=10, height=5)
    llamar(s, "create_sketch", plane="XY", name="B")
    r = llamar(s, "include_3d_geometry", faces=[">Z"])
    assert len(r["entities"]) == 4
    assert sorted(c["length"] for c in entidades3d(s)) == pytest.approx([10, 10, 20, 20])


def test_sk_incluir_3d_sigue_al_modelo_y_con_link_falso_queda_congelado(s):
    """Con vínculo (link) las aristas acompañan al modelo; con link=false quedan congeladas."""
    llamar(s, "create_parameter", name="largo", expression="20 mm")
    llamar(s, "create_box", length="largo", width=10, height=5)
    llamar(s, "create_sketch", plane="XY", name="A")
    llamar(s, "include_3d_geometry", faces=[">Z"])
    llamar(s, "set_parameter", name="largo", expression="30 mm")
    assert sorted(c["length"] for c in entidades3d(s)) == pytest.approx([10, 10, 30, 30])

    s2 = api.Sesion()
    llamar(s2, "create_parameter", name="largo", expression="20 mm")
    llamar(s2, "create_box", length="largo", width=10, height=5)
    llamar(s2, "create_sketch", plane="XY", name="B")
    r = llamar(s2, "include_3d_geometry", faces=[">Z"], link=False)
    assert r["linked"] is False
    llamar(s2, "set_parameter", name="largo", expression="30 mm")
    assert sorted(c["length"] for c in entidades3d(s2)) == pytest.approx([10, 10, 20, 20])
