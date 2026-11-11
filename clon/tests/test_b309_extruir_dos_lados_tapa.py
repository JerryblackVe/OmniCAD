# -*- coding: utf-8 -*-
"""B-309 (guardia): en la pieza de Gerardo, Extruir el círculo Ø31 con «Dos lados» (−15 / 10 mm) o «Un lado» −15 y Unir
a la tapa daba «resultado imposible» (7446,63 mm³ fuera de 18 869,2 a 26 751,7). La tapa salía de partir con un plano un
disco unido a un buje Ø31 con rosca interior que termina justo en ese plano, y Gerardo la había subido 0,1 mm siguiendo
el consejo del mensaje. Rearmado el 2026-11-11 (la tapa da 7882,5178 mm³, la misma del error), une bien en main."""
import math

import pytest

from omnicad import api


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def tapa():
    s = api.Sesion()
    _ok(s, "create_cylinder", height=5, radius=22.5, name="Tapa")
    _ok(s, "create_cylinder", height=15, radius=15.5, z=-15, operation="join", target="Tapa")
    _ok(s, "create_cylinder", height=15, radius=14, z=-15, name="Eje")
    _ok(s, "create_thread", faces=["%CYLINDER"], body="Eje", thread="M28")
    _ok(s, "boolean_operation", target="Tapa", tools=["Eje"], operation="cut", keep_tools=True)
    _ok(s, "create_construction_plane", plane="XY", offset=0, name="P")
    _ok(s, "split_body", body="Tapa", tool="P")
    buje = next(b["id"] for b in _ok(s, "get_scene_info")["bodies"] if b["name"] not in ("Tapa", "Eje"))
    _ok(s, "move_body", body="Tapa", translate=[0, 0, 0.1])
    _ok(s, "remove_bodies", bodies=buje)
    _ok(s, "create_sketch", plane="XY", name="B")
    _ok(s, "draw_circle", sketch="B", radius=15.5)
    return s


def _volumen(s):
    return _ok(s, "get_physical_properties", bodies=["Tapa"])["bodies"][0]["volume"]


def test_dos_lados_con_lado_negativo_une_a_la_tapa(tapa):
    disco = _volumen(tapa)
    assert disco == pytest.approx(math.pi * 22.5 ** 2 * 5, rel=1e-6)
    _ok(tapa, "extrude", sketch="B", profile=0, operation="join", target="Tapa", direction="two_sides",
        distance=-15, distance2=10)
    # cada lado es una magnitud (B-205): 15 mm hacia arriba (tapa 0,1–5,1) y 10 hacia abajo
    esperado = disco + math.pi * 15.5 ** 2 * (25 - 5)
    assert _volumen(tapa) == pytest.approx(esperado, rel=1e-6)


def test_un_lado_negativo_queda_separado_por_el_hueco(tapa):
    disco = _volumen(tapa)
    r = _ok(tapa, "extrude", sketch="B", profile=0, operation="join", target="Tapa", direction="one_side", distance=-15)
    # la tapa quedó 0,1 mm arriba: el cilindro no la toca y la unión lo avisa, pero no pierde material
    assert r["bodies_modified"][0]["volume"] == pytest.approx(disco + math.pi * 15.5 ** 2 * 15, rel=1e-6)
