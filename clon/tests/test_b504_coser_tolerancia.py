# -*- coding: utf-8 -*-
"""B-504: Coser con una tolerancia tan grande como la pieza daba «ok» con una forma vacía (1e6) o un sólido falso
(un tubo abierto cerrado desde 45 mm), y el cuerpo vacío rompía get_scene_info."""
import pytest
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import superficies as sf


def _tubo():
    """Las 4 caras laterales de una caja de 60×40×20 (sin tapas)."""
    return [c for c in sf.descoser(geo.caja(60, 40, 20)) if geo.caja_envolvente(c)[1][2] - geo.caja_envolvente(c)[0][2] > 1]


def test_coser_rechaza_una_tolerancia_tan_grande_como_la_pieza():
    assert not sf.coser(_tubo(), 9)["es_solido"]                     # menos de la mitad de 20 mm: cose normal
    for tol in (10, 100, 1e6):
        with pytest.raises(geo.ErrorGeometria, match="⚠ Tolerancia demasiado grande.*menos de 10 mm"):
            sf.coser(_tubo(), tol)
    with pytest.raises(geo.ErrorGeometria, match="demasiado grande"):
        sf.bordes_de_costura(_tubo(), 1e6)                           # la tabla del panel e inspect_stitch, igual


def test_una_chapa_plana_con_ruido_en_z_no_frena_la_costura():
    """Una chapa importada con 0,0001 mm de ruido en Z cuenta como plana: el tope sale de 60×40, no de 0,0001."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt
    def parche(x0, x1, z):
        p = BRepBuilderAPI_MakePolygon(gp_Pnt(x0, 0, 0), gp_Pnt(x1, 0, z), gp_Pnt(x1, 40, z), gp_Pnt(x0, 40, 0), True)
        return BRepBuilderAPI_MakeFace(p.Wire(), False).Face()
    assert sf.coser([parche(0, 30, 1e-4), parche(30, 60, 0)], 0.01)["aristas_cosidas"] == 1


def test_una_superficie_vacia_no_rompe_la_normal_de_muestra():
    vacia = TopoDS_Compound()
    BRep_Builder().MakeCompound(vacia)
    with pytest.raises(geo.ErrorGeometria, match="no tiene caras"):
        sf.normal_muestra(vacia)


def test_stitch_surfaces_1e6_da_error_y_deja_el_documento_como_estaba():
    s = api.Sesion()
    caja = api.llamar(s, "create_surface_box", {"length": 60, "width": 40, "height": 20})
    assert caja["ok"], caja
    caja = [b["id"] for b in api.llamar(s, "get_scene_info")["result"]["bodies"]]
    assert api.llamar(s, "unstitch_surfaces", {"bodies": caja})["ok"]
    cuerpos = [b["id"] for b in api.llamar(s, "get_scene_info")["result"]["bodies"]]
    r = api.llamar(s, "stitch_surfaces", {"bodies": cuerpos, "tolerance": 1e6})
    assert not r["ok"] and "⚠ Tolerancia demasiado grande" in r["mensaje"], r
    info = api.llamar(s, "get_scene_info")
    assert info["ok"] and len(info["result"]["bodies"]) == len(cuerpos), info
    r = api.llamar(s, "stitch_surfaces", {"bodies": cuerpos})
    assert r["ok"] and api.llamar(s, "get_scene_info")["result"]["bodies"][0]["type"] == "solid", r
