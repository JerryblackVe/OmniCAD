"""B-619: la silueta de un cuerpo de revolución visto de costado son sus meridianos (el perfil girado), con los polos del
perfil y sin desvío. El HLR de OpenCascade daba exacto solo el lado de la costura; el otro, aproximado: 65 a 72 polos de
grado 8 a 0,12 mm (en la PC de Gerardo, con picos y polos sueltos lejos de la curva)."""
import math

import numpy as np
import pytest
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_BSplineCurve

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import perfiles


def _polos_meridianos(forma):
    return max(BRepAdaptor_Curve(a).BSpline().NbPoles() for a in geo._aristas_unicas(forma)
               if BRepAdaptor_Curve(a).GetType() == GeomAbs_BSplineCurve)


@pytest.fixture(scope="module")
def barril():
    s = api.Sesion()

    def llamar(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, r)
    llamar("create_sketch", plane="XZ", name="Perfil")
    llamar("draw_line", start_x=0, start_y=0, end_x=30, end_y=0)
    llamar("draw_spline", points=[[30, 0], [35, 8], [38, 20], [38.5, 32], [36, 45]])
    llamar("draw_spline", points=[[36, 45], [39, 55], [40, 65], [37.5, 80], [32, 90]])
    llamar("draw_line", start_x=32, start_y=90, end_x=0, end_y=90)
    llamar("draw_line", start_x=0, start_y=90, end_x=0, end_y=0)
    llamar("revolve", sketch="Perfil", profile=0, axis="z")
    return s.cuerpo("Cuerpo1").forma


def _distancia_a_la_superficie(forma, punto):
    """Los planos de la prueba contienen el eje: la silueta exacta cae sobre la superficie del cuerpo."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    return BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, punto))).Vertex(), forma).Value()


@pytest.mark.parametrize("normal, u", [((0, 1, 0), (1, 0, 0)), ((1, 0, 0), (0, 1, 0)), ((0.6, 0.8, 0), (0.8, -0.6, 0))],
                         ids=["XZ", "YZ", "oblicuo"])
def test_silueta_del_barril_son_sus_meridianos_con_pocos_polos(barril, normal, u):
    perfiles._CACHE_SILUETA.clear()
    plano = geo.Plano.desde_marco((0, 0, 0), normal, u)
    prims, sueltos = perfiles.silueta_forma(barril, plano)
    curvas = [p for p in prims if p[0] == "spline"]
    assert len(curvas) == 4 and not sueltos
    assert max(len(p[2]) for p in curvas) <= _polos_meridianos(barril)  # sin más polos que el perfil real
    for p in curvas:                                      # cada punto de la silueta, sobre la superficie
        for q in perfiles.puntos_primitiva(p, 40):
            punto = plano.pnt(*q)
            assert _distancia_a_la_superficie(barril, punto.Coord()) < 1e-4, punto.Coord()
    for p in curvas:                                      # sin polos sueltos: cerca de su curva
        muestras = np.array(perfiles.puntos_primitiva(p, 200))
        lejos = max(float(np.min(np.linalg.norm(muestras - q, axis=1))) for q in p[2])
        assert lejos < 3.0


def test_un_plano_que_no_es_paralelo_al_eje_sigue_igual(barril):
    """Visto en diagonal no hay meridianos: queda lo que da el HLR, cerrado y sin sueltos."""
    perfiles._CACHE_SILUETA.clear()
    n = np.array([0.0, math.sqrt(0.5), math.sqrt(0.5)])
    prims, sueltos = perfiles.silueta_forma(barril, geo.Plano.desde_marco((0, 0, 0), tuple(n), (1, 0, 0)))
    assert prims and not sueltos


def test_b619a_intersecar_por_el_eje_da_el_perfil_exacto(barril):
    """El corte por un plano que contiene el eje es el perfil girado: antes, 2 splines de 1001 polos."""
    plano = geo.Plano.desde_marco((0, 0, 0), (0, 1, 0), (1, 0, 0))
    prims, sueltos = perfiles.intersecar_forma(barril, plano)
    curvas = [p for p in prims if p[0] == "spline"]
    assert len(curvas) == 4 and not sueltos and max(len(p[2]) for p in curvas) <= _polos_meridianos(barril)
    for p in curvas:
        for q in perfiles.puntos_primitiva(p, 40):
            assert _distancia_a_la_superficie(barril, plano.pnt(*q).Coord()) < 1e-4


def test_b619a_un_corte_que_no_pasa_por_el_eje_sigue_siendo_el_de_opencascade(barril):
    prims, _ = perfiles.intersecar_forma(barril, geo.Plano.desde_marco((0, 10, 0), (0, 1, 0), (1, 0, 0)))
    assert len([p for p in prims if p[0] == "spline"]) >= 2


def test_b619a_pared_fina_no_pierde_el_corte_del_agujero():
    """Exterior de revolución (spline) y agujero cilíndrico a 0,4–0,7 mm: el corte del agujero no cae «sobre» el
    meridiano exterior (la holgura del corte es de 0,01 % del tamaño)."""
    s = api.Sesion()
    for nombre, a in (("create_sketch", {"plane": "XZ", "name": "Perfil"}),
                      ("draw_line", {"start_x": 29.6, "start_y": 0, "end_x": 30, "end_y": 0}),
                      ("draw_spline", {"points": [[30, 0], [30.3, 40], [30.2, 80]]}),
                      ("draw_line", {"start_x": 30.2, "start_y": 80, "end_x": 29.6, "end_y": 80}),
                      ("draw_line", {"start_x": 29.6, "start_y": 80, "end_x": 29.6, "end_y": 0}),
                      ("revolve", {"sketch": "Perfil", "profile": 0, "axis": "z"})):
        assert api.llamar(s, nombre, a)["ok"]
    prims, _ = perfiles.intersecar_forma(s.cuerpo("Cuerpo1").forma,
                                         geo.Plano.desde_marco((0, 0, 0), (0, 1, 0), (1, 0, 0)))
    verticales = [p for p in prims if p[0] == "linea" and abs(p[2][0] - p[3][0]) < 1e-6 and abs(abs(p[2][0]) - 29.6) < 1e-6]
    assert len(verticales) == 2
