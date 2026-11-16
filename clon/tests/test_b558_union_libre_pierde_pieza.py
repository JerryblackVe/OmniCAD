"""B-558: con caras B-spline las booleanas no controlaban el volumen y una unión de dos sólidos pegados por una cara
podía perder uno sin error (B-536b: cavidad 3250,8 + prisma 70,6 = 3250,8). Ahora es un problema que dispara el
reintento; una pieza B-spline enterrada (unión = la grande) no es un falso positivo."""
import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm


@pytest.fixture(scope="module")
def cavidad_y_prisma():
    s = api.Sesion()
    for nombre, args in (("create_sketch", {"plane": "XY", "name": "perfil"}), ("draw_circle", {"radius": 5}),
                         ("create_sketch", {"plane": "XZ", "name": "ruta"}),
                         ("draw_spline", {"points": [[0, 0], [30, 10], [60, 0], [90, 10]]}),
                         ("sweep", {"sketch": "perfil", "path_sketch": "ruta"}),
                         ("fillet", {"body": "Cuerpo1", "edges": "all", "radius": 1})):
        assert api.llamar(s, nombre, args)["ok"], nombre
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    tapa = next(c for c in geo.caras(forma) if sm._plano_de_cara(c) is not None)
    cavidad, plano = sm._desfase_cuerpo(forma, -1.0, sm.GeomAbs_Arc), sm._plano_de_cara(tapa)
    prisma = BRepPrimAPI_MakePrism(sm._tapa_del_hueco(cavidad, plano, 1.0)[0],
                                   gp_Vec(*(np.asarray(plano.normal, float) * 1.5))).Shape()     # pegado por la tapa
    assert geo.es_forma_libre(cavidad) and geo._volumenes_entrada(cavidad, prisma) is None
    return cavidad, prisma


def test_la_union_que_perdio_el_prisma_no_es_creible(cavidad_y_prisma):
    cavidad, prisma = cavidad_y_prisma
    problema = geo._problema_booleana(cavidad, prisma, "unir", cavidad, None)      # lo que devolvía el kernel
    assert problema is not None and problema[0] == 2 and "perdió una pieza" in problema[1]


def test_la_union_suma_el_prisma_o_da_error_nunca_lo_pierde_callada(cavidad_y_prisma):
    """El kernel pierde el prisma o no según el estado de memoria: lo que se garantiza es no devolverlo perdido."""
    cavidad, prisma = cavidad_y_prisma
    try:
        union = geo.booleano(cavidad, prisma, "unir")
    except geo.ErrorGeometria as e:
        assert "perdió una pieza" in str(e)
        return
    assert geo.volumen_exacto(union) == pytest.approx(geo.volumen_exacto(cavidad) + geo.volumen_exacto(prisma), rel=1e-3)


def test_una_pieza_libre_enterrada_no_es_un_falso_positivo():
    grande = BRepBuilderAPI_NurbsConvert(geo.caja(20, 20, 20), True).Shape()
    chica = BRepBuilderAPI_NurbsConvert(geo.caja(4, 4, 4, origen=(8, 8, 8)), True).Shape()
    assert geo._volumenes_entrada(grande, chica) is None
    assert geo._problema_booleana(grande, chica, "unir", grande, None) is None
