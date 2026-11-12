# -*- coding: utf-8 -*-
"""B-310: el desfase de la cara de un cilindro con un chaflán en el borde fallaba «en el kernel» en cuanto la cara se
metía más que el chaflán (pieza de Gerardo: Ø31 con chaflán de 1 mm, −1,24 y −6,13 mm). Como Fusion, el chaflán
consumido desaparece y la cara se desfasa igual. Caso mínimo también en tests/corpus_caza/b310_desfase_chaflan.json."""
import math

import pytest

from omnicad import api


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _cilindro_con_chaflan():
    s = api.Sesion()
    _ok(s, "create_cylinder", height=15, radius=15.5)
    _ok(s, "chamfer", edges="<Z", distance=1)
    cara = next(c for c in _ok(s, "find_faces", body="Cuerpo1")["faces"]
                if c["type"] == "cylinder" and abs(c["radius"] - 15.5) < 1e-6)
    return s, cara["id"]


@pytest.mark.parametrize("distancia", [-1.24, -6.13])
def test_desfase_hacia_adentro_mas_que_el_chaflan(distancia):
    s, cara = _cilindro_con_chaflan()
    _ok(s, "offset_faces", faces=[cara], distance=distancia)
    geo = _ok(s, "check_geometry", body="Cuerpo1")["bodies"][0]
    assert geo["valid"] and geo["closed"]
    r = 15.5 + distancia            # el chaflán se consumió: queda el cilindro liso de radio r
    assert geo["volume"] == pytest.approx(math.pi * r * r * 15, rel=1e-6)


def test_desfase_que_no_consume_el_chaflan_lo_conserva():
    s, cara = _cilindro_con_chaflan()
    _ok(s, "offset_faces", faces=[cara], distance=-0.5)
    caras = _ok(s, "find_faces", body="Cuerpo1")["faces"]
    assert any(c["type"] == "cone" for c in caras)


def _cara(forma, tipo):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    ex = TopExp_Explorer(forma, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face(ex.Current())
        if BRepAdaptor_Surface(f).GetType() == tipo:
            return f
        ex.Next()


@pytest.mark.parametrize("r_chico, dist, esperado", [(14.5, -1.24, True), (14.5, -0.5, False), (5.5, -1.24, False)])
def test_solo_se_quita_el_cono_que_el_desfase_traga_entero(r_chico, dist, esperado):
    """Un cono más ancho que el desfase (pieza cónica de verdad) no se quita con defeaturing."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone, BRepPrimAPI_MakeCylinder
    from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder

    from omnicad.nucleo.solidos_modificar import _consumido
    cono = _cara(BRepPrimAPI_MakeCone(15.5, r_chico, 1.0).Shape(), GeomAbs_Cone)
    cilindro = _cara(BRepPrimAPI_MakeCylinder(15.5, 15.0).Shape(), GeomAbs_Cylinder)
    assert _consumido(cono, cilindro, dist) is esperado
