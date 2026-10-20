"""Pruebas numéricas de división y eliminación por MCP/CLI."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    resultado = api.llamar(sesion, nombre, args)
    assert resultado["ok"], resultado
    return resultado["result"]


def caja():
    sesion = api.Sesion()
    resultado = llamar(sesion, "create_box", length=10, width=10, height=10)
    return sesion, resultado["bodies_created"][0]["id"]


def comprobar(sesion, cuerpo, volumen):
    forma = sesion.cuerpo(cuerpo).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(volumen)
    return forma


def test_dividir_cuerpo_y_deshacer():
    s, cid = caja()
    resultado = llamar(s, "split_body", body="Cuerpo1", tool="YZ")
    assert resultado["feature"]["type"] == "dividir_cuerpo"
    assert len(s.doc.estado_final.cuerpos) == 2
    volumenes = [geo.volumen(comprobar(s, c, 500)) for c in s.doc.estado_final.cuerpos]
    assert sum(volumenes) == pytest.approx(1000)
    llamar(s, "undo")
    assert len(s.doc.estado_final.cuerpos) == 1
    comprobar(s, cid, 1000)


def test_dividir_cuerpo_con_cuerpo_herramienta():
    s, cid = caja()
    herramienta = llamar(s, "create_cylinder", radius=2, height=20, z=-5, name="Corte")["bodies_created"][0]["id"]
    r = llamar(s, "split_body", body=cid, tool="Corte")
    assert len(r["bodies_created"]) == 1
    assert len(s.doc.estado_final.cuerpos) == 3
    comprobar(s, herramienta, math.pi * 80)
    volumenes = [geo.volumen(c.forma) for c in s.doc.estado_final.cuerpos.values() if c.id != herramienta]
    assert sorted(volumenes) == pytest.approx(sorted([40 * math.pi, 1000 - 40 * math.pi]))
    assert all(geo.es_valida(c.forma) for c in s.doc.estado_final.cuerpos.values())


def test_dividir_cara_solo_parte_la_tapa():
    s, cid = caja()
    cara = llamar(s, "find_faces", body=cid, selector=">Z")["faces"][0]["id"]
    r = llamar(s, "split_face", faces=cara, tool="YZ", extend=True)
    assert r["feature"]["type"] == "dividir_cara"
    forma = comprobar(s, cid, 1000)
    assert len(geo.caras(forma)) == 7
    assert sorted(geo.area(c) for c in geo.caras(forma))[:2] == pytest.approx([50, 50])
    assert len(s.doc.estado_final.cuerpos) == 1


def test_division_silueta():
    s = api.Sesion()
    cid = llamar(s, "create_cylinder", radius=5, height=10)["bodies_created"][0]["id"]
    r = llamar(s, "silhouette_split", body=cid, direction="X")
    assert r["feature"]["type"] == "division_silueta"
    forma = comprobar(s, cid, math.pi * 250)
    assert len(geo.caras(forma)) == 4


def test_reemplazar_cara():
    s, cid = caja()
    plano = llamar(s, "create_construction_plane", plane="XY", offset=15)["plane"]["id"]
    r = llamar(s, "replace_face", faces=">Z", target=plano, body=cid)
    assert r["feature"]["type"] == "reemplazar_cara"
    comprobar(s, cid, 1500)


def test_quitar_cuerpos():
    s, cid = caja()
    r = llamar(s, "remove_bodies", bodies=["Cuerpo1", cid])
    assert r["feature"]["type"] == "quitar"
    assert r["bodies_removed"] == [cid]
    assert llamar(s, "get_scene_info", summary=True)["counts"]["bodies"] == 0


def test_borrar_cara_del_agujero():
    s, cid = caja()
    llamar(s, "create_hole", body=cid, face=">Z", diameter=4, through_all=True)
    comprobar(s, cid, 1000 - 40 * math.pi)
    r = llamar(s, "delete_faces", body=cid, faces="%CYLINDER")
    assert r["feature"]["type"] == "borrar_caras"
    forma = comprobar(s, cid, 1000)
    assert len(geo.caras(forma)) == 6


@pytest.mark.parametrize("nombre,args", [
    ("split_body", {"body": "Ausente", "tool": "XY"}),
    ("split_face", {"faces": ">Z", "tool": "O"}),
    ("delete_faces", {"faces": []}),
    ("remove_bodies", {"bodies": []}),
])
def test_errores_atomicos(nombre, args):
    s, cid = caja()
    antes = s.doc.a_dict()
    r = api.llamar(s, nombre, args)
    assert not r["ok"], r
    assert r["error_kind"] in {"BODY_NOT_FOUND", "INVALID_ARGUMENTS"}
    assert s.doc.a_dict() == antes
    comprobar(s, cid, 1000)
