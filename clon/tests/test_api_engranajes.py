# -*- coding: utf-8 -*-
"""Herramientas de engranajes y ejes de la API (`api/herramientas_engranajes.py`): gear_info, create_gear,
create_gear_pair (con su ensamblaje), create_rack, create_sprocket y create_shaft."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import engranajes as en
from omnicad.nucleo import geometria as geo


@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def falla(sesion, nombre, kind="INVALID_ARGUMENTS", **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def caja(sesion, cid):
    (a, b) = geo.caja_envolvente(sesion.cuerpo(cid).forma)
    return [round(v, 4) for v in a + b]


def test_registradas_en_el_grupo_solido():
    nombres = {h["nombre"] for h in api.catalogo("solido")}
    assert {"gear_info", "create_gear", "create_gear_pair", "create_rack", "create_sprocket", "create_shaft"} <= nombres


def test_gear_info_z20_m2_y_par(s):
    r = llamar(s, "gear_info", module=2, teeth=20, teeth2=40)
    assert (r["pitch_diameter"], r["tip_diameter"], r["root_diameter"]) == (40.0, 44.0, 35.0)
    assert r["circular_pitch"] == pytest.approx(2 * math.pi, abs=1e-4) and r["undercut"] is False
    assert r["min_teeth_no_undercut"] == 18 and r["min_teeth_theoretical"] == pytest.approx(17.0973, abs=1e-4)
    par = r["pair"]
    assert par["center_distance"] == 60.0 and par["ratio"] == 2.0 and par["interference"] is False
    assert par["contact_ratio"] == pytest.approx(1.635, abs=1e-3) and par["gear2"]["tip_diameter"] == 84.0
    assert llamar(s, "gear_info", module=2, teeth=12)["undercut"] is True
    falla(s, "gear_info", module=2, teeth=2)
    falla(s, "gear_info", module=-1, teeth=20)
    assert s.doc.operaciones == []                       # solo calcula


def test_create_gear_en_un_plano_con_parametros(s):
    llamar(s, "create_parameter", name="z", expression="24")
    r = llamar(s, "create_gear", module=2, teeth="z", width=6, bore=8, plane="XZ", center=[10, 5])
    assert r["feature"]["type"] == "engranaje" and r["gear"]["tip_diameter"] == 52.0
    (cuerpo,) = r["bodies_created"]
    assert cuerpo["name"] == "Engranaje z24" and cuerpo["volume"] > 0
    x0, y0, z0, x1, y1, z1 = caja(s, cuerpo["id"])
    assert (x1, y0, y1) == (36.0, -6.0, 0.0)            # el primer diente apunta al eje x del plano; normal de XZ: −Y
    llamar(s, "set_parameter", name="z", expression="30")
    assert caja(s, cuerpo["id"])[3] == 42.0
    paso = r["feature"]["id"]
    llamar(s, "edit_feature", feature=paso, params={"helice": "15 deg"})
    assert geo.es_valida(s.cuerpo(cuerpo["id"]).forma)
    r = falla(s, "create_gear", "OPERATION_FAILED", module=2, teeth=8, profile_shift=1.5)
    assert "en punta" in r["mensaje"] and len(s.doc.operaciones) == 1


def test_create_gear_pair_con_ensamblaje_en_un_paso_de_deshacer(s):
    r = llamar(s, "create_gear_pair", module=2, teeth1=20, teeth2=40, width=4)
    assert r["center_distance"] == 60.0 and r["ratio"] == 2.0 and r["interference"] is False
    assert [b["name"] for b in r["bodies_created"]] == ["Engranaje z20", "Engranaje z40"]
    a = r["assembly"]
    assert len(a["components"]) == 2 and len(a["joints"]) == 2 and a["motion_link"]
    tl = llamar(s, "get_timeline", include_params=False)["steps"]
    assert [p["type"] for p in tl] == ["engranaje", "componente", "componente", "union", "union", "vinculo_movimiento"]
    assert all(p["status"] == "ok" for p in tl)
    c1, c2 = (s.cuerpo(b["id"]).forma for b in r["bodies_created"])
    inter = geo.booleano(c1, c2, "intersecar")
    assert geo.esta_vacia(inter) or abs(geo.volumen(inter)) < 1e-6
    llamar(s, "undo")
    assert s.doc.operaciones == []
    r = llamar(s, "create_gear_pair", module=2, teeth1=18, teeth2=30, direction=90, rotation=4, assembly=False)
    assert r["assembly"] is None and len(s.doc.operaciones) == 1 and s.doc.operaciones[0].p["giro"] == "4.0"
    x0, y0, _z0, x1, y1, _z1 = caja(s, r["bodies_created"][1]["id"])
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx((0, 48), abs=0.6)


def test_create_rack_y_create_sprocket(s):
    r = llamar(s, "create_rack", module=2, teeth=6, width=5, height=10, center=[0, 50])
    assert r["rack"]["length"] == pytest.approx(6 * math.pi * 2, abs=1e-4) and r["rack"]["pitch"] == pytest.approx(
        2 * math.pi, abs=1e-4)
    x0, y0, _z0, x1, y1, _z1 = caja(s, r["bodies_created"][0]["id"])
    assert (x0, x1, y0, y1) == pytest.approx((0, 12 * math.pi, 40, 52), abs=1e-4)
    r = llamar(s, "create_sprocket", teeth=20, chain="08B", bore=10)
    d = r["sprocket"]
    assert d["pitch_diameter"] == pytest.approx(12.7 / math.sin(math.pi / 20), abs=1e-4)
    assert d["width"] == pytest.approx(0.93 * 7.75, abs=1e-3)
    r = llamar(s, "create_sprocket", teeth=12, chain="custom", pitch=8, roller_diameter=5, width=2.8)
    assert r["sprocket"]["pitch"] == 8.0 and geo.es_valida(s.cuerpo(r["bodies_created"][0]["id"]).forma)
    assert "hacen falta" in falla(s, "create_sprocket", teeth=12, chain="custom", pitch=8)["mensaje"]
    assert "ya trae paso" in falla(s, "create_sprocket", teeth=12, chain="10A", pitch=8)["mensaje"]
    falla(s, "create_sprocket", teeth=12, chain="99Z")
    falla(s, "create_gear", teeth=20)                     # módulo y dientes son obligatorios


def test_create_shaft_volumen_y_agujero_escalonado(s):
    segmentos = [{"diameter": 20, "length": 30, "start": "chamfer", "start_size": 1},
                 {"diameter": 30, "length": 20, "end": "fillet", "end_size": 2},
                 {"diameter": 16, "length": "largo_punta"}]
    llamar(s, "create_parameter", name="largo_punta", expression="25 mm")
    r = llamar(s, "create_shaft", segments=segmentos)
    tramos = [{"diametro": 20, "largo": 30, "inicio": "chaflan", "medida_inicio": 1},
              {"diametro": 30, "largo": 20, "fin": "empalme", "medida_fin": 2}, {"diametro": 16, "largo": 25}]
    assert r["shaft"] == {"length": 75.0, "max_diameter": 30.0, "volume": round(en.volumen_eje(tramos), 4)}
    assert r["bodies_created"][0]["volume"] == pytest.approx(en.volumen_eje(tramos), abs=1e-3)
    assert caja(s, r["bodies_created"][0]["id"])[5] == 75.0
    caja_id = llamar(s, "create_box", length=40, width=40, height=20, x=100)["bodies_created"][0]["id"]
    r = llamar(s, "create_shaft", segments=[{"diameter": 10, "length": 8}, {"diameter": 6, "length": 20}],
               center=[100, 0], operation="cut", target=caja_id)
    assert r["bodies_modified"][0]["volume"] == pytest.approx(40 * 40 * 20 - math.pi * (25 * 8 + 9 * 12), abs=1e-3)
    falla(s, "create_shaft", segments=[])
    falla(s, "create_shaft", segments=[{"diameter": 10, "lenght": 8}])
    falla(s, "create_shaft", segments=[{"diameter": 10, "length": 8, "start": "chamfer"}])
    falla(s, "create_shaft", segments=[{"diameter": 10, "length": 8, "start": "bisel", "start_size": 1}])
    r = falla(s, "create_shaft", "OPERATION_FAILED",
              segments=[{"diameter": 10, "length": 2, "start": "chamfer", "start_size": 3}])
    assert "no entra" in r["mensaje"]
