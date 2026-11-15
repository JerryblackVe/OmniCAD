"""B-451: la Solevación con un punto que no sirve (el centro del círculo, en el plano del perfil, o al menos un perfil)
da un error claro en vez de «el kernel no pudo» o un sólido plano de volumen 0."""
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _circulo(radio=10.0):
    arista = BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), radio)).Edge()
    return BRepBuilderAPI_MakeWire(arista).Wire()


def _punto(z):
    return BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, z)).Vertex()


@pytest.mark.parametrize("orden", ["perfil_punto", "punto_perfil"])
def test_el_centro_en_el_plano_del_perfil_da_error_claro(orden):
    secciones = [_circulo(), _punto(0)] if orden == "perfil_punto" else [_punto(0), _circulo()]
    with pytest.raises(geo.ErrorGeometria, match="en el plano del perfil"):
        sc.solevar(secciones)


def test_solo_puntos_da_error_claro():
    with pytest.raises(geo.ErrorGeometria, match="al menos un perfil") as e:
        sc.solevar([_punto(0), _punto(5)])
    assert "kernel" not in str(e.value)


def test_un_punto_fuera_del_plano_sigue_valiendo_como_punta():
    cono = sc.solevar([_circulo(), _punto(5)])
    assert geo.es_valida(cono)
    assert geo.volumen(cono) == pytest.approx(3.141592653589793 * 100 * 5 / 3, rel=1e-3)


def test_punto_en_el_plano_del_vecino_vale_con_una_seccion_intermedia():
    # Revisión de Sol: círculo R10 → círculo R5 en Z5 → punto en Z5 es un solevado liso válido.
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt
    c = gp_Circ(gp_Ax2(gp_Pnt(0, 0, 5), gp_Dir(0, 0, 1)), 5.0)
    chico = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(c).Edge()).Wire()
    forma = sc.solevar([_circulo(), chico, _punto(5)])
    assert geo.es_valida(forma)
