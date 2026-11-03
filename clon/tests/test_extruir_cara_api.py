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


def test_b164_dos_caras_de_distinta_direccion_fallan_con_un_error_claro():
    """B-164: la caja vaciada 80 × 60 × 40 (pared 2, sin tapa) tiene F2 en la cara -Y y F3 en la -X. Extruildas
    juntas, cada cara sale en su propia normal y el paso dejaba un cuerpo de volumen 0 (y el STEP perdía ese cuerpo).
    En Fusion las caras de una extrusión tienen que ser coplanares: acá el paso tiene que fallar y no tocar nada."""
    s = api.Sesion()
    ok(s, "create_box", length=80, width=60, height=40, name="Cuerpo1")
    ok(s, "shell", body="Cuerpo1", thickness=2, faces=">Z")
    api.llamar(s, "find_faces", {})                    # los ids de cara valen hasta el próximo cambio del documento
    ok(s, "extrude", faces=["Cuerpo1/F2"])
    antes = [(b["name"], b["volume"]) for b in ok(s, "get_scene_info")["bodies"]]
    api.llamar(s, "find_faces", {})
    r = api.llamar(s, "extrude", {"faces": ["Cuerpo1/F2", "Cuerpo1/F3"]})
    assert not r["ok"], r
    assert r["error_kind"] == "OPERATION_FAILED", r
    assert "cada cara por separado" in r["mensaje"], r
    assert [(b["name"], b["volume"]) for b in ok(s, "get_scene_info")["bodies"]] == antes


def test_dos_caras_paralelas_del_mismo_lado_se_extruyen_juntas():
    """Las tapas de dos cajas separadas (paralelas, del mismo lado y a distinta altura) sí se extruyen en un paso:
    dan dos cuerpos, cada uno con su volumen."""
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, x=0, name="CajaA")
    ok(s, "create_box", length=20, width=20, height=10, x=50, name="CajaB")
    caras = [ok(s, "find_faces", body=nombre, selector=">Z")["faces"][0]["id"] for nombre in ("CajaA", "CajaB")]
    ok(s, "extrude", faces=caras, distance=5)
    cuerpos = ok(s, "get_scene_info")["bodies"]
    assert len(cuerpos) == 4
    assert sorted(c["volume"] for c in cuerpos[2:]) == [2000.0, 2000.0]
