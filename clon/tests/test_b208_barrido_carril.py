"""B-208: el carril orienta sin deformar las secciones del barrido de Fusion."""
import math

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakePolygon
from OCP.GC import GC_MakeArcOfCircle
from OCP.gp import gp_Pnt

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import superficies as sf


def _linea(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge()


@pytest.mark.parametrize("superficie", [False, True])
@pytest.mark.parametrize("escala, final", [("ninguna", 2), ("ninguna", 6), ("escalar", 2), ("escalar", 6)])
def test_b208_carril_recto_conserva_el_prisma_o_el_tronco(superficie, escala, final):
    perfil = BRepBuilderAPI_MakePolygon()
    for p in [(0, -2, -2), (0, 2, -2), (0, 2, 2), (0, -2, 2)]:
        perfil.Add(gp_Pnt(*p))
    perfil.Close()
    ruta = _linea((0, 0, 0), (50, 0, 0))
    carril = _linea((0, 0, 2), (50, 0, final))
    lado_final = 4 if escala == "ninguna" else 2 * final
    if superficie:
        forma = sf.barrer_superficie(perfil.Wire(), ruta, carril=carril, escala=escala)
        esperado = 4 * (4 + lado_final) / 2 * math.hypot(50, (lado_final - 4) / 2)
        assert geo.area(forma) == pytest.approx(esperado, rel=1e-6)
    else:
        forma = sc.barrer(perfil.Wire(), ruta, carril=carril, escala_carril=escala)
        esperado = 50 / 3 * (16 + lado_final ** 2 + 4 * lado_final)
        assert geo.volumen(forma) == pytest.approx(esperado, rel=1e-6)
    assert geo.es_valida(forma)
    minimo, maximo = geo.caja_envolvente(forma)
    assert minimo == pytest.approx((0, -lado_final / 2, -lado_final / 2), abs=1e-4)
    assert maximo == pytest.approx((50, lado_final / 2, lado_final / 2), abs=1e-4)


@pytest.mark.parametrize("superficie", [False, True])
def test_b208_carril_concentrico_acompana_la_ruta_curva(superficie):
    perfil = BRepBuilderAPI_MakePolygon()
    for p in [(18, 0, -2), (22, 0, -2), (22, 0, 2), (18, 0, 2)]:
        perfil.Add(gp_Pnt(*p))
    perfil.Close()

    def arco(radio):
        curva = GC_MakeArcOfCircle(gp_Pnt(radio, 0, 0),
                                  gp_Pnt(radio / math.sqrt(2), radio / math.sqrt(2), 0),
                                  gp_Pnt(0, radio, 0)).Value()
        return BRepBuilderAPI_MakeEdge(curva).Edge()

    if superficie:
        forma = sf.barrer_superficie(perfil.Wire(), arco(20), carril=arco(22), escala="ninguna")
        medida = geo.area(forma)
    else:
        forma = sc.barrer(perfil.Wire(), arco(20), carril=arco(22), escala_carril="ninguna")
        medida = geo.volumen(forma)
    assert geo.es_valida(forma)
    assert medida == pytest.approx(16 * 20 * math.pi / 2, rel=1e-5)


@pytest.mark.parametrize("superficie", [False, True])
def test_b208_api_y_recalculo_conservan_las_secciones(superficie):
    from omnicad import api

    sesion = api.Sesion()

    def llamar(nombre, **args):
        resultado = api.llamar(sesion, nombre, args)
        assert resultado["ok"], resultado
        return resultado["result"]

    llamar("create_sketch", plane="YZ", name="Perfil")
    llamar("draw_rectangle", sketch="Perfil", x1=-2, y1=-2, x2=2, y2=2)
    llamar("create_sketch", plane="XY", name="Ruta")
    ruta = llamar("draw_line", sketch="Ruta", start_x=0, start_y=0, end_x=50, end_y=0)
    llamar("create_sketch", plane="XZ", name="Carril")
    carril = llamar("draw_line", sketch="Carril", start_x=0, start_y=2, end_x=50, end_y=6)
    if superficie:
        llamar("create_surface_sweep", profiles={"sketch": "Perfil", "profile": 0},
               path={"sketch": "Ruta", "curve": ruta["entities"][0]["id"]},
               guide_rail={"sketch": "Carril", "curve": carril["entities"][0]["id"]})
    else:
        llamar("sweep", sketch="Perfil", path_sketch="Ruta", rail_sketch="Carril")
    for _ in range(2):
        forma = list(sesion.doc.estado_final.cuerpos.values())[-1].forma
        assert geo.es_valida(forma)
        medida = geo.area(forma) if superficie else geo.volumen(forma)
        esperado = 32 * math.hypot(50, 4) if superficie else 50 / 3 * (16 + 144 + 48)
        assert medida == pytest.approx(esperado, rel=1e-6)
        sesion.doc.recalcular(0)


def test_b208_extension_completa_con_distancias_distintas_no_exige_cruce_normal():
    forma = sf.barrer_superficie(_linea((0, 0, 0), (10, 0, 0)),
                                _linea((0, 0, 0), (0, 0, 100)),
                                carril=_linea((10, 0, 0), (10, 0, 100)),
                                extension="completa", distancia_carril=0.5, escala="ninguna")
    assert geo.es_valida(forma)
    assert geo.area(forma) == pytest.approx(1000, rel=1e-6)
