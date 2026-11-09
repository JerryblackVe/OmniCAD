# -*- coding: utf-8 -*-
"""P-121: la caja envolvente exacta se guarda por forma. La ventana la pedía 10 a 16 veces al aceptar un comando
(~50 ms cada una en un cuerpo de 400 caras) solo para elegir la finura del teselado."""
import pytest
from OCP.BRep import BRep_Builder
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Trsf, gp_Vec

from omnicad.nucleo import geometria as geo


@pytest.fixture
def consultas(monkeypatch):
    """Cuenta las consultas exactas al kernel."""
    cuenta = []

    class Contador:
        @staticmethod
        def AddOptimal_s(*a):
            cuenta.append(1)
            return geo.BRepBndLib.__wrapped__.AddOptimal_s(*a)

    Contador.__wrapped__ = geo.BRepBndLib
    monkeypatch.setattr(geo, "BRepBndLib", Contador)
    monkeypatch.setattr(geo, "_CAJAS", {})
    return cuenta


def test_la_misma_forma_no_se_vuelve_a_medir(consultas):
    caja = geo.caja(10, 20, 30)
    primera = geo.caja_envolvente(caja)
    assert primera == (pytest.approx((0, 0, 0)), pytest.approx((10, 20, 30)))
    assert geo.caja_envolvente(caja) == primera and len(consultas) == 1


def test_movida_es_otra_caja(consultas):
    caja = geo.caja(10, 10, 10)
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(100, 0, 0))
    movida = caja.Moved(TopLoc_Location(t))
    assert geo.caja_envolvente(caja)[0][0] == pytest.approx(0)
    assert geo.caja_envolvente(movida)[0][0] == pytest.approx(100)


def test_un_compuesto_que_crece_se_vuelve_a_medir(consultas):
    b, c = BRep_Builder(), TopoDS_Compound()
    b.MakeCompound(c)
    b.Add(c, geo.caja(10, 10, 10))
    assert geo.caja_envolvente(c)[1][0] == pytest.approx(10)
    b.Add(c, geo.caja(10, 10, 10, origen=(50, 0, 0)))
    assert geo.caja_envolvente(c)[1][0] == pytest.approx(60)


def test_el_tope_suelta_las_viejas(consultas):
    assert geo._TOPE_CAJAS <= 16        # cada entrada retiene una forma vieja con su malla: la memoria de la PC manda
    for i in range(geo._TOPE_CAJAS + 5):
        geo.caja_envolvente(geo.caja(1, 1, 1, origen=(i, 0, 0)))
    assert len(geo._CAJAS) == geo._TOPE_CAJAS
