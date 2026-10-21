"""B-52: una bobina cónica incrustada debe fusionarse sin perder material."""
import math

import numpy as np
import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.GeomAbs import GeomAbs_BSplineSurface
from OCP.gp import gp_Pnt, gp_Vec
from scipy.stats import qmc

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rv
from omnicad.nucleo import solidos_crear as sc


def _campana_y_bobina():
    perfil = BRepBuilderAPI_MakePolygon()
    for radio, z in ((43, 0), (15, 45), (12, 45), (40, 0)):
        perfil.Add(gp_Pnt(radio, 0, z))
    perfil.Close()
    cara = BRepBuilderAPI_MakeFace(perfil.Wire()).Face()
    campana = geo.revolver([cara], (0, 0, 0), (0, 0, 1), 360)
    # El anillo de refuerzo cruza la hélice: el cono liso solo no reproduce B-52.
    campana = geo.booleano(campana, geo.toroide(32, 3, (0, 0, 20)), "unir")
    bobina = sc.bobina((0, 0, 0), (0, 0, 1), diametro=87, revoluciones=6,
                       altura=45, angulo=-31.9, tamano_seccion=2, eje_x=(1, 0, 0))
    return campana, bobina


def _integrar_bobina(bobina, contiene):
    """Cuadratura Sobol del interior barrido, sin booleanas ni clasificación de la bobina.

    X(u,v,r) = C(v) + r·(S(u,v)−C(v)); C es el centro de cada sección circular.
    Con r=√w, el peso es |(S−C)·(Su×(Cv+r·(Sv−Cv)))|/2.
    El jacobiano integra el volumen real incluso con una sección oblicua a la ruta.
    """
    sup = next(BRepAdaptor_Surface(c) for c in geo.caras(bobina)
               if BRepAdaptor_Surface(c).GetType() == GeomAbs_BSplineSurface)
    u0, u1 = sup.FirstUParameter(), sup.LastUParameter()
    v0, v1 = sup.FirstVParameter(), sup.LastVParameter()
    p, du, dv, p0, du0, dv0, p1, du1, dv1 = (
        gp_Pnt(), gp_Vec(), gp_Vec(), gp_Pnt(), gp_Vec(), gp_Vec(), gp_Pnt(), gp_Vec(), gp_Vec())
    muestras = qmc.Sobol(3, scramble=True, seed=52).random_base2(16)
    volumen, solape = 0.0, 0.0
    for uu, vv, rr in muestras:
        u, v, r = u0 + (u1 - u0) * uu, v0 + (v1 - v0) * vv, math.sqrt(rr)
        sup.D1(u, v, p, du, dv)
        sup.D1(u0, v, p0, du0, dv0)
        sup.D1((u0 + u1) / 2, v, p1, du1, dv1)
        centro = (np.array(p0.Coord()) + p1.Coord()) / 2
        radial = gp_Vec(*(np.array(p.Coord()) - centro))
        derivada_centro = (dv0 + dv1) * 0.5
        derivada = derivada_centro + (dv - derivada_centro) * r
        peso = abs(radial.Dot(du.Crossed(derivada))) * (u1 - u0) * (v1 - v0) / (2 * len(muestras))
        punto = centro + r * np.array(radial.Coord())
        volumen += peso
        if contiene(punto):
            solape += peso
    return volumen, solape


def _comprobar(campana, bobina, volumen_solape):
    union = geo.booleano(campana, bobina, "unir")
    solape = geo.booleano(campana, bobina, "intersecar")
    corte = geo.booleano(bobina, campana, "cortar")
    volumen_a, volumen_b = geo.volumen(campana), geo.volumen(bobina)
    print(f"B-52: campana={volumen_a:.6f}, bobina={volumen_b:.6f}, "
          f"union={geo.volumen(union):.6f}, solidos={len(geo.solidos(union))}, "
          f"solape={geo.volumen(solape):.6f}, solape_independiente={volumen_solape:.6f}, "
          f"corte={geo.volumen(corte):.6f}")
    assert len(geo.solidos(union)) == 1
    assert geo.es_valida(union)
    assert rv.es_estanca(union)
    assert geo.volumen(union) == pytest.approx(volumen_a + volumen_b - volumen_solape, rel=0.01)
    assert geo.volumen(corte) + volumen_solape == pytest.approx(volumen_b, rel=0.01)
    assert geo.volumen(solape) == pytest.approx(volumen_solape, rel=0.01)
    assert geo.es_valida(corte) and rv.es_estanca(corte)
    assert geo.es_valida(solape) and rv.es_estanca(solape)


def test_bobina_conica_incrustada_conserva_material():
    campana, bobina = _campana_y_bobina()

    def contiene(punto):
        x, y, z = punto
        radio = math.hypot(x, y)
        return ((0 <= z <= 45 and 40 - 28 / 45 * z <= radio <= 43 - 28 / 45 * z)
                or (radio - 32) ** 2 + (z - 20) ** 2 <= 9)

    volumen, solape = _integrar_bobina(bobina, contiene)
    assert volumen == pytest.approx(geo.volumen(bobina), rel=0.001)
    assert 0 < solape < volumen
    _comprobar(campana, bobina, solape)
