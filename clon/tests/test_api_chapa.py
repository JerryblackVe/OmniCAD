# -*- coding: utf-8 -*-
"""Herramientas del grupo "chapa" (api/herramientas_chapa.py): reglas propias, pestañas, dobladillo, plegar,
desplegar, patrón plano, convertir, desgarro, unir plegando, reglas de un cuerpo y DXF. Cuentas exactas con el
factor K: un pliegue de 90° desarrolla π/2 · (R + K·t)."""
import json
import math

import pytest

from omnicad import api
from omnicad.io_archivos.dxf import leer_dxf
from omnicad.nucleo import analisis as an
from omnicad.nucleo import chapa
from omnicad.nucleo import geometria as g
from omnicad.timeline.documento import Documento

T, R, K = 2.0, 2.0, 0.44                     # «Acero 2 mm»
BA90 = math.pi / 2 * (R + K * T)
VOL_PESTANA = 100 * 46 * T + math.pi / 2 * T * (R + T / 2) * 100 + 100 * 16 * T     # placa + pestaña de 20


@pytest.fixture(autouse=True)
def bibliotecas(tmp_path, monkeypatch):
    """Las bibliotecas del usuario van a archivos temporales y se restauran: los tests no tocan las reales."""
    monkeypatch.setenv(chapa.VAR_REGLAS, str(tmp_path / "reglas_chapa.json"))
    monkeypatch.setenv(an.VAR_MATERIALES, str(tmp_path / "materiales.json"))
    monkeypatch.setattr(chapa, "REGLAS_USUARIO", {})
    copia = dict(an.TABLA_MATERIALES)
    yield tmp_path
    an.TABLA_MATERIALES.clear()
    an.TABLA_MATERIALES.update(copia)


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def falla(s, nombre, kind, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta          # atómica: el documento no cambió
    return r


def caja(s, cid):
    return [round(v, 4) for p in g.caja_envolvente(s.cuerpo(cid).forma) for v in p]


def placa(s, regla="Acero 2 mm", **extra):
    """Pestaña base de 100 × 50 sobre XY (de 0 a 100 y de 0 a 50)."""
    bid = llamar(s, "create_sketch", plane="XY")["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=100, y2=50, sketch=bid)
    r = llamar(s, "create_base_flange", sketch=bid, rule=regla, **extra)
    return r["bodies_created"][0]["id"], r


def con_pestana(s):
    cid, _ = placa(s)
    r = llamar(s, "create_edge_flange", edges="nearest:[50,50,2]", body=cid, height=20)
    return cid, r


# ---------------------------------------------------------------- reglas
def test_reglas_de_fabrica_y_errores_de_regla():
    s = api.Sesion()
    reglas = {r["name"]: r for r in llamar(s, "list_sheet_metal_rules")["rules"]}
    assert set(chapa.REGLAS) <= set(reglas)
    assert reglas["Acero 2 mm"] == dict(reglas["Acero 2 mm"], source="builtin", thickness=2.0, bend_radius=2.0,
                                        k_factor=0.44, material="Acero")
    falla(s, "create_sheet_metal_rule", "NAME_EXISTS", name="acero 2 MM", thickness=3)
    falla(s, "create_sheet_metal_rule", "INVALID_ARGUMENTS", name="Mala", thickness=1, k_factor=1.5)
    falla(s, "create_sheet_metal_rule", "INVALID_ARGUMENTS", name="Mala", thickness=-1)
    r = falla(s, "create_sheet_metal_rule", "MATERIAL_NOT_FOUND", name="Mala", thickness=1, material="Kriptonita")
    assert "list_materials" in " ".join(r["pistas"])
    bid = llamar(s, "create_sketch", plane="XY")["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=10, sketch=bid)
    r = falla(s, "create_base_flange", "SHEET_METAL_RULE_NOT_FOUND", sketch=bid, rule="Cartón 3 mm")
    assert "Acero 2 mm" in r["mensaje"]
    falla(s, "delete_sheet_metal_rule", "INVALID_ARGUMENTS", name="Acero 1 mm")
    falla(s, "delete_sheet_metal_rule", "SHEET_METAL_RULE_NOT_FOUND", name="No existe")


def test_regla_propia_da_el_desarrollo_la_masa_y_viaja_en_la_receta(bibliotecas):
    s = api.Sesion()
    r = llamar(s, "create_sheet_metal_rule", name="Latón 0.8 mm", thickness=0.8, k_factor=0.4, bend_radius=1.0,
               material="latón")
    assert r["rule"] == dict(r["rule"], thickness=0.8, bend_radius=1.0, k_factor=0.4, material="Latón",
                             relief_width=0.8, relief_depth=0.4, gap=0.8, source="user")
    guardado = json.loads((bibliotecas / "reglas_chapa.json").read_text(encoding="utf-8"))
    assert guardado["reglas"]["Latón 0.8 mm"]["k"] == 0.4
    falla(s, "create_sheet_metal_rule", "NAME_EXISTS", name="latón 0.8 mm", thickness=1)

    cid, res = placa(s, "LATÓN 0.8 MM")                            # sin distinguir mayúsculas
    (info,) = res["sheet_metal"]
    assert info["rule"]["name"] == "Latón 0.8 mm" and info["material"] == "Latón"
    assert res["bodies_created"][0]["volume"] == pytest.approx(100 * 50 * 0.8)
    paso = s.paso(res["feature"]["id"])
    assert paso.p["regla"] == "Latón 0.8 mm" and paso.p["regla_propia"]["k"] == 0.4      # copia en la receta
    masa = llamar(s, "get_physical_properties", bodies=[cid])["bodies"][0]
    assert masa["material"] == "Latón" and masa["mass_g"] == pytest.approx(4000 * 8.47e-3)

    llamar(s, "create_edge_flange", edges="nearest:[50,50,0.8]", body=cid, height=20)
    t, rr, k = 0.8, 1.0, 0.4
    alto = 50 + 20 + math.pi / 2 * (rr + k * t) - 2 * (rr + t)
    info = llamar(s, "get_sheet_metal_info", body=cid)["bodies"][0]
    assert info["flat_size"] == pytest.approx([100, alto], abs=1e-4) and info["bends"] == 1

    # Otra PC (sin la regla en su biblioteca): la receta abre igual y la regla aparece como «del documento».
    chapa.REGLAS_USUARIO.clear()
    otra = api.Sesion(Documento.desde_dict(s.doc.a_dict()))
    assert llamar(otra, "get_sheet_metal_info", body=cid)["bodies"][0]["flat_size"] == pytest.approx([100, alto],
                                                                                                    abs=1e-4)
    reglas = {x["name"]: x for x in llamar(otra, "list_sheet_metal_rules")["rules"]}
    assert reglas["Latón 0.8 mm"]["source"] == "document" and reglas["Latón 0.8 mm"]["used_by"] == ["op2"]
    # …y se puede seguir usando por nombre en ese documento.
    _, res2 = placa(otra, "Latón 0.8 mm")
    assert res2["sheet_metal"][0]["rule"]["k_factor"] == 0.4

    # Se carga en la próxima sesión desde el .json.
    assert chapa.cargar_reglas_propias() == ["Latón 0.8 mm"]
    llamar(s, "delete_sheet_metal_rule", name="latón 0.8 mm")
    assert "Latón 0.8 mm" not in chapa.REGLAS_USUARIO
    assert json.loads((bibliotecas / "reglas_chapa.json").read_text(encoding="utf-8"))["reglas"] == {}


def test_set_sheet_metal_rule_cambia_espesor_y_regla_y_recalcula():
    s = api.Sesion()
    cid, _ = con_pestana(s)
    r = llamar(s, "set_sheet_metal_rule", body=cid, thickness=3, k_factor=0.5)
    assert r["before"]["rule"]["thickness"] == 2 and r["after"]["rule"]["thickness"] == 3
    assert r["after"]["rule"]["k_factor"] == 0.5 and r["after"]["bends"] == 1
    assert s.paso("op2").p["ajustes"] == {"espesor": "3.0", "k": "0.5"}
    r = llamar(s, "set_sheet_metal_rule", body=cid, reset=True, rule="Aluminio 1.5 mm")
    assert r["after"]["rule"] == dict(r["after"]["rule"], name="Aluminio 1.5 mm", thickness=1.5, k_factor=0.44)
    assert r["after"]["material"] == "Aluminio 6061"
    llamar(s, "undo")
    assert llamar(s, "get_sheet_metal_info", body=cid)["bodies"][0]["rule"]["thickness"] == 3


# ---------------------------------------------------------------- pestañas, dobladillo, plegar
def test_pestana_de_arista_desplegar_replegar_patron_y_dxf(tmp_path):
    s = api.Sesion()
    cid, r = con_pestana(s)
    assert r["bodies_modified"][0]["volume"] == pytest.approx(VOL_PESTANA)
    assert caja(s, cid) == [0, 0, 0, 100, 50, 20]
    desarrollo = 50 + 20 + BA90 - 2 * (R + T)                     # 66,524 mm
    assert r["sheet_metal"][0]["flat_size"] == pytest.approx([100, desarrollo], abs=1e-4)

    r = llamar(s, "unfold", face="nearest:[50,25,2]", body=cid)
    assert r["bodies_modified"][0]["volume"] == pytest.approx(100 * desarrollo * T)
    assert caja(s, cid) == pytest.approx([0, 0, 0, 100, desarrollo, 2], abs=1e-4)
    assert r["sheet_metal"][0]["unfolded_bends"] == 1
    r = llamar(s, "refold", body=cid)
    assert r["feature"]["name"] == "Replegado1" and r["bodies_modified"][0]["volume"] == pytest.approx(VOL_PESTANA)
    assert caja(s, cid) == [0, 0, 0, 100, 50, 20]

    r = llamar(s, "create_flat_pattern", face="nearest:[50,25,2]", body=cid, location="beside")
    (patron,) = r["bodies_created"]
    assert patron["volume"] == pytest.approx(100 * desarrollo * T)
    assert r["sheet_metal"][0]["is_flat_pattern"] and r["sheet_metal"][0]["flat_pattern_of"] == cid
    assert caja(s, patron["id"])[0] == pytest.approx(110)          # al lado de la pieza, 10 mm más allá

    ruta = tmp_path / "plano"
    r = llamar(s, "export_flat_pattern_dxf", path=str(ruta), body=cid, bend_extensions=True)
    assert r["path"].endswith("plano.dxf") and r["flat_size"] == pytest.approx([100, desarrollo], abs=1e-4)
    capas = {}
    for capa, prim in leer_dxf(tmp_path / "plano.dxf", con_capas=True):
        capas.setdefault(capa, []).append(prim)
    assert len(capas["LINEAS_PLIEGUE"]) == 1 and len(capas["EXTENSION_PLIEGUE"]) == 2
    falla(s, "export_flat_pattern_dxf", "FILE_EXISTS", path=str(tmp_path / "plano.dxf"), body=cid)
    r = llamar(s, "export_flat_pattern_dxf", path=str(tmp_path / "plano.dxf"), body=patron["id"],
               bend_centerlines=False, overwrite=True)
    assert r["body"] == patron["id"]
    assert not any(capa == "LINEAS_PLIEGUE" for capa, _ in leer_dxf(tmp_path / "plano.dxf", con_capas=True))


def test_dobladillo_cerrado_y_abierto():
    s = api.Sesion()
    cid, _ = placa(s)
    r = llamar(s, "create_hem", edges="nearest:[50,50,2]", body=cid, length=10)
    assert r["bodies_modified"][0]["volume"] == pytest.approx(10000 + math.pi * T ** 2 / 2 * 100 + 8 * 100 * T)
    assert caja(s, cid)[3:] == pytest.approx([100, 52, 4])
    s = api.Sesion()
    cid, _ = placa(s)
    r = llamar(s, "create_hem", edges="nearest:[50,50,2]", body=cid, hem_type="open", gap=1, length=10)
    assert r["bodies_modified"][0]["volume"] == pytest.approx(10000 + math.pi * T * 1.5 * 100 + 7.5 * 100 * T)


def test_pestana_de_contorno_en_l():
    s = api.Sesion()
    bid = llamar(s, "create_sketch", plane="XZ")["sketch"]["id"]
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=50, end_y=0, sketch=bid)
    llamar(s, "draw_line", start_x=50, start_y=0, end_x=50, end_y=30, sketch=bid)
    r = llamar(s, "create_contour_flange", sketch=bid, distance=40, rule="Acero 2 mm")
    (c,) = r["bodies_created"]
    assert c["volume"] == pytest.approx((46 + 26) * 40 * T + math.pi / 2 * T * (R + T / 2) * 40)
    assert caja(s, c["id"]) == [0, -40, 0, 50, 0, 30]
    assert r["sheet_metal"][0]["flat_size"] == pytest.approx([40, 72 + BA90], abs=1e-4)      # 40 × 76,524
    falla(s, "create_contour_flange", "ENTITY_NOT_FOUND", sketch=bid, curves=[99])


def test_plegar_por_una_linea_de_boceto_sobre_la_cara():
    s = api.Sesion()
    cid, _ = placa(s)
    bid = llamar(s, "create_sketch", plane=">Z", body=cid)["sketch"]["id"]
    llamar(s, "draw_line", start_x=60, start_y=0, end_x=60, end_y=50, sketch=bid)
    r = llamar(s, "fold", face=">Z", body=cid, sketch=bid, angle=90, fixed_point=[20, 25, 2])
    assert r["bodies_modified"][0]["volume"] == pytest.approx(10000 - BA90 * 50 * T
                                                              + math.pi / 2 * T * (R + T / 2) * 50)
    ini = 60 - BA90 / 2                                            # la línea queda en el centro del pliegue
    assert caja(s, cid)[3:] == pytest.approx([ini + R + T, 50, 100 - ini - BA90 + R + T], abs=1e-4)
    assert r["sheet_metal"][0]["flat_area"] == pytest.approx(5000)


# ---------------------------------------------------------------- convertir, desgarro, unir plegando
def test_convertir_a_chapa_toma_el_espesor_medido_y_el_material_de_la_regla():
    s = api.Sesion()
    cid = llamar(s, "create_box", length=100, width=50, height=3)["bodies_created"][0]["id"]
    r = llamar(s, "convert_to_sheet_metal", face=">Z", rule="Acero inoxidable 1.2 mm")
    (info,) = r["sheet_metal"]
    assert info["id"] == cid and info["rule"]["thickness"] == pytest.approx(3) and info["rule"]["bend_radius"] == 3
    assert info["material"] == "Acero inoxidable"
    falla(s, "convert_to_sheet_metal", "INVALID_ARGUMENTS", face=">Z")                   # ya es de chapa
    falla(s, "set_sheet_metal_rule", "INVALID_ARGUMENTS", body=cid, thickness=5)         # espesor medido
    llamar(s, "create_edge_flange", edges="nearest:[0,25,3]", body=cid, height=20)
    assert caja(s, cid)[3:] == pytest.approx([50, 25, 20])


def test_desgarro_por_cara_y_por_puntos():
    s = api.Sesion()
    cid, _ = con_pestana(s)
    pliegue = llamar(s, "find_faces", body=cid, selector="%CYLINDER")["faces"][0]["id"]   # un id de find_faces
    r = llamar(s, "rip", face=pliegue)                             # quita el pliegue
    vols = sorted(b["volume"] for b in r["bodies_modified"] + r["bodies_created"])
    assert vols == pytest.approx([100 * 16 * T, 100 * 46 * T])
    assert len(r["sheet_metal"]) == 2

    s = api.Sesion()
    cid, _ = placa(s)
    puntos = llamar(s, "sketch_from_spec", plane=">Z", body=cid, entities=[
        {"type": "point", "at": [30, 0], "id": "a"}, {"type": "point", "at": [30, 50], "id": "b"}])
    bid, h = puntos["sketch"]["id"], puntos["handles"]
    r = llamar(s, "rip", face=">Z", body=cid, mode="points", gap=1,
               points=[{"sketch": bid, "point": h["a"]}, {"sketch": bid, "point": h["b"]}])
    vols = sorted(b["volume"] for b in r["bodies_modified"] + r["bodies_created"])
    assert vols == pytest.approx([29.5 * 50 * T, 69.5 * 50 * T])

    s = api.Sesion()                                               # por vértices: ranura sobre el borde x = 0
    cid, _ = placa(s)
    r = llamar(s, "rip", face=">Z", body=cid, mode="points", gap=1, points=[[0, 0, 2], [0, 50, 2]])
    assert r["bodies_modified"][0]["volume"] == pytest.approx(99.5 * 50 * T)
    r = falla(s, "rip", "ELEMENT_NOT_FOUND", face=">Z", body=cid, mode="points", points=[[10, 0, 2], [0, 50, 2]])
    assert "más cercano" in r["mensaje"]
    falla(s, "rip", "INVALID_ARGUMENTS", face=">Z", body=cid, mode="points", points=[[0, 0, 2]])


def test_unir_plegando_dos_chapas():
    s = api.Sesion()
    a, _ = placa(s)
    plano = llamar(s, "create_construction_plane", plane="XZ", offset=-60)["plane"]["id"]
    bid = llamar(s, "create_sketch", plane=plano)["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=0, y1=10, x2=100, y2=40, sketch=bid)
    b = llamar(s, "create_base_flange", sketch=bid, rule="Acero 2 mm")["bodies_created"][0]["id"]
    assert caja(s, b) == [0, 58, 10, 100, 60, 40]
    r = llamar(s, "join_by_bend", edge1="nearest:[50,50,2]", body1=a, edge2="nearest:[50,58,10]", body2=b)
    assert r["bodies_removed"] == [b] and list(s.doc.estado_final.cuerpos) == [a]
    assert r["bodies_modified"][0]["volume"] == pytest.approx(100 * 56 * T + 100 * 36 * T
                                                              + math.pi / 2 * T * (R + T / 2) * 100)
    assert caja(s, a) == [0, 0, 0, 100, 60, 40]
    assert r["sheet_metal"][0]["flat_size"][1] == pytest.approx(56 + BA90 + 36)


def test_errores_de_cuerpo_de_chapa():
    s = api.Sesion()
    caja_id = llamar(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    assert llamar(s, "get_sheet_metal_info")["bodies"] == []
    falla(s, "get_sheet_metal_info", "NOT_SHEET_METAL", body=caja_id)
    falla(s, "refold", "NOT_SHEET_METAL")
    falla(s, "export_flat_pattern_dxf", "NOT_SHEET_METAL", path="x.dxf")
    falla(s, "create_edge_flange", "OPERATION_FAILED", edges=">Z and >Y", body=caja_id)
