"""B-494: `geo.longitud` mide la elipse con la integración exacta (antes GProp: 134,244 en vez de 133,649)."""
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Ax2, gp_Dir, gp_Elips, gp_Pnt
from scipy.special import ellipe

from omnicad.nucleo import analisis, curvas3d
from omnicad.nucleo import geometria as geo

EXACTO = 4 * 30 * ellipe(1 - (10 / 30) ** 2)        # perímetro de la elipse de semiejes 30 y 10: 133,6489…


def _elipse():
    return BRepBuilderAPI_MakeEdge(gp_Elips(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 30, 10)).Edge()


def test_elipse_arista_alambre_y_cara_miden_el_perimetro_exacto():
    arista = _elipse()
    cara = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(arista).Wire()).Face()
    assert geo.es_valida(cara)
    for forma in (arista, cara):
        assert geo.longitud(forma) == pytest.approx(EXACTO, abs=1e-6)
    assert analisis.medir(arista)["a"]["largo"] == pytest.approx(EXACTO, abs=1e-6)
    assert curvas3d.longitud(arista) == geo.longitud(arista)


def test_las_aristas_compartidas_cuentan_por_cara_como_antes():
    assert geo.longitud(BRepPrimAPI_MakeBox(1, 2, 3).Shape()) == pytest.approx(4 * (1 + 2 + 3) * 2)
