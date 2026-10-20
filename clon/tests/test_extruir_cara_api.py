# -*- coding: utf-8 -*-
"""Extruir SOLO una cara de un cuerpo con la herramienta `extrude` (la misma operación que «Extruir cara» de la tira
flotante): join la empuja hacia afuera (agrega material), cut hacia adentro (corta) sin pedir reverse. Volúmenes exactos."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def caja():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")
    return s


def cuerpo(s):
    return ok(s, "get_scene_info")["bodies"][0]


@pytest.mark.parametrize("cara", [">Z", "<Z", ">X"])
def test_join_empuja_la_cara_hacia_afuera_en_cualquier_lado(cara):
    s = caja()
    ok(s, "extrude", faces=cara, operation="join", distance=5, body="Caja")
    assert len(ok(s, "get_scene_info")["bodies"]) == 1
    assert cuerpo(s)["volume"] == pytest.approx(8000 + 400 * 5)


@pytest.mark.parametrize("cara", [">Z", "<Z", ">X"])
def test_cut_empuja_la_cara_hacia_adentro_sin_pedir_reverse(cara):
    s = caja()
    ok(s, "extrude", faces=cara, operation="cut", distance=5, body="Caja")
    assert cuerpo(s)["volume"] == pytest.approx(8000 - 400 * 5)
    assert geo.es_valida(s.doc.estado_final.cuerpos["op1.c1"].forma)


def test_reverse_explicito_manda_sobre_el_automatico():
    s = caja()
    ok(s, "extrude", faces=">Z", operation="cut", distance=5, reverse=False, body="Caja")   # hacia afuera: no corta nada
    assert cuerpo(s)["volume"] == pytest.approx(8000)


def test_cara_curva_no_se_extruye():
    s = api.Sesion()
    ok(s, "create_cylinder", radius=10, height=20, name="Cil")
    r = api.llamar(s, "extrude", {"faces": "%CYLINDER", "operation": "join", "distance": 5, "body": "Cil"})
    assert not r["ok"], r
    assert cuerpo(s)["volume"] == pytest.approx(3.141592653589793 * 100 * 20)       # el cuerpo no cambió
