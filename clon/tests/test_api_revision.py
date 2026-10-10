# -*- coding: utf-8 -*-
"""Herramientas check_geometry, check_printability y repair_body (api/herramientas_revision.py)."""
import json

import pytest
from OCP.BRep import BRep_Builder
from OCP.ShapeFix import ShapeFix_ShapeTolerance
from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import intercambio


def ok(r):
    assert r["ok"], r
    return r["result"]


def falla(r, kind):
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def caja_rota():
    """Caja 10×20×30 con una cara al revés (inválida) y tolerancias de 0,5 mm."""
    caras = geo.caras(geo.caja(10, 20, 30))
    sh, so, b = TopoDS_Shell(), TopoDS_Solid(), BRep_Builder()
    b.MakeShell(sh)
    for i, f in enumerate(caras):
        b.Add(sh, f.Reversed() if i == 0 else f)
    b.MakeSolid(so)
    b.Add(so, sh)
    ShapeFix_ShapeTolerance().SetTolerance(so, 0.5)
    return so


@pytest.fixture
def rota():
    s = api.Sesion()
    llamar(s, "run_operation", type="operacion_base",
           params={"cuerpos": [{"id": "x.c1", "nombre": "Rota", "tipo": "solido",
                                "brep": intercambio.brep_a_texto(caja_rota())}]})
    return s


def test_check_geometry_del_ejemplo_todo_bien():
    s = api.Sesion(crear_documento_ejemplo())
    r = llamar(s, "check_geometry")
    assert r["count"] == 2 and r["all_valid"] and r["all_closed"]
    for b in r["bodies"]:
        assert b["valid"] and b["closed"] and b["type"] == "solid" and b["issues"] == [] and b["errors"] == 0
        assert b["free_edges"] == b["non_manifold_edges"] == b["self_intersections"] == 0
        assert b["max_tolerance"]["edge"] <= 1e-6 and b["volume"] > 0 and "Válido: sí" in b["summary"]
    json.dumps(r)


def test_check_geometry_cuerpo_roto(rota):
    r = llamar(rota, "check_geometry", body="Rota", max_issues=5)
    (b,) = r["bodies"]
    assert not r["all_valid"] and not b["valid"] and b["errors"] >= 1 and b["high_tolerances"] == 26
    assert b["issues"][0]["kind"] == "invalid_shell" and b["issues"][0]["severity"] == "error"
    assert len(b["issues"][0]["position"]) == 3 and len(b["issues"]) == 5 and b["issues_truncated"]
    assert {i["kind"] for i in b["issues"][1:]} == {"high_tolerance"} and b["issues"][1]["value"] == pytest.approx(0.5)
    assert b["max_tolerance"] == {"vertex": 0.5, "edge": 0.5, "face": 0.5}
    assert llamar(rota, "check_geometry", body="Rota", tolerance_limit=1.0)["bodies"][0]["high_tolerances"] == 0


def test_check_geometry_caja_sin_tapa_y_mallas():
    s = api.Sesion()
    cid = llamar(s, "create_box", length=10, width=20, height=30)["bodies_created"][0]["id"]
    llamar(s, "run_operation", type="teselar", params={"cuerpos": [cid], "mantener": True})
    malla = next(b for b in llamar(s, "get_scene_info")["bodies"] if b["type"] == "mesh")
    r = llamar(s, "check_geometry", body=malla["id"])["bodies"][0]
    assert r["type"] == "mesh" and r["valid"] and r["closed"] and r["inverted_normals"] == 0
    assert r["self_intersections"] is None and r["max_tolerance"] is None and not r["negative_volume"]
    assert r["volume"] == pytest.approx(6000)


def test_check_printability_placa_fina_y_voladizo():
    s = api.Sesion()
    placa = llamar(s, "create_box", length=20, width=20, height=0.3)["bodies_created"][0]["id"]
    r = llamar(s, "check_printability", body=placa, min_thickness=0.8)
    (b,) = r["bodies"]
    assert not r["all_printable"] and not b["printable"] and b["closed"]
    assert b["min_thickness_measured"] == pytest.approx(0.3) and b["thin_regions"] == 1
    assert b["issues"][0]["kind"] == "thin_wall" and b["issues"][0]["value"] == pytest.approx(0.3)
    assert r["settings"] == {"min_thickness": 0.8, "overhang_angle": 45.0, "sharp_angle": 20.0}
    cubo = llamar(s, "create_box", length=10, width=10, height=10, x=100)["bodies_created"][0]["id"]
    llamar(s, "move_body", body=cubo, rotate=[30, 0, 0])
    b = llamar(s, "check_printability", body=cubo)["bodies"][0]
    assert b["printable"] and b["overhang_area"] == pytest.approx(100, rel=1e-5) and b["overhang_regions"] == 1
    assert [i["kind"] for i in b["issues"]] == ["overhang"] and b["issues"][0]["severity"] == "warning"
    json.dumps(r)


@pytest.mark.parametrize("nombre, args", [
    ("check_printability", {"overhang_angle": 95}), ("check_printability", {"min_thickness": -1}),
    ("check_printability", {"samples": 0}), ("check_printability", {"sharp_angle": 180}),
    ("check_geometry", {"tolerance_limit": 0}), ("check_geometry", {"max_issues": -1}),
    ("repair_body", {"body": "Cuerpo1", "tolerance": -1})])
def test_argumentos_invalidos(nombre, args):
    s = api.Sesion(crear_documento_ejemplo())
    falla(api.llamar(s, nombre, args), "INVALID_ARGUMENTS")


def test_cuerpo_inexistente_y_documento_vacio():
    s = api.Sesion()
    falla(api.llamar(s, "check_geometry", {}), "NOTHING_TO_MEASURE")
    falla(api.llamar(s, "check_printability", {"body": "nada"}), "BODY_NOT_FOUND")
    falla(api.llamar(s, "repair_body", {"body": "nada"}), "BODY_NOT_FOUND")


def test_repair_body_arregla_deja_un_paso_y_se_deshace(rota):
    pasos = len(rota.doc.operaciones)
    r = llamar(rota, "repair_body", body="Rota", tolerance=0.001)
    assert r["feature"]["type"] == "reparar_cuerpo" and r["feature"]["name"] == "Reparar1"
    assert r["before"] == {"valid": False, "closed": True, "free_edges": 0, "non_manifold_edges": 0,
                           "max_tolerance": 0.5}
    assert r["after"]["valid"] and r["after"]["closed"] and r["after"]["max_tolerance"] <= 0.001
    assert r["bodies_modified"][0]["volume"] == pytest.approx(6000)
    assert len(rota.doc.operaciones) == pasos + 1 and rota.doc.operaciones[-1].p["tolerancia"] == "0.001"
    assert llamar(rota, "check_geometry", body="Rota")["all_valid"]
    llamar(rota, "edit_feature", feature=r["feature"]["id"], params={"tolerancia": "0.002 mm"})
    assert llamar(rota, "check_geometry", body="Rota")["bodies"][0]["max_tolerance"]["edge"] <= 0.002
    llamar(rota, "undo")
    llamar(rota, "undo")
    assert len(rota.doc.operaciones) == pasos and not llamar(rota, "check_geometry", body="Rota")["all_valid"]


def test_repair_body_en_malla():
    s = api.Sesion()
    cid = llamar(s, "create_box", length=10, width=20, height=30)["bodies_created"][0]["id"]
    llamar(s, "run_operation", type="teselar", params={"cuerpos": [cid], "mantener": False})
    malla = llamar(s, "get_scene_info")["bodies"][0]
    r = llamar(s, "repair_body", body=malla["id"])
    assert r["before"]["closed"] and r["after"]["closed"] and r["after"]["max_tolerance"] is None


def test_describe_operation_reparar():
    d = llamar(api.Sesion(), "describe_operation", type="reparar_cuerpo")
    assert d["label"] == "Reparar cuerpo" and [p["name"] for p in d["params"]] == ["cuerpos", "tolerancia", "coser",
                                                                                  "refinar", "arreglar"]
    assert d["expressions"] == ["tolerancia"]
