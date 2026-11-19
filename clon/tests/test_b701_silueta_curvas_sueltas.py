"""B-701: la silueta de un cuerpo (Proyectar con el filtro Cuerpos) da perfiles cerrados, como Fusion: una arista
del HLR que queda suelta adentro de la sombra (libre o pegada al borde) no sale como curva del boceto."""
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import gp_Pnt

from omnicad.nucleo import geometria as g
from omnicad.nucleo import perfiles as pf


def _seg(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*a, 0), gp_Pnt(*b, 0)).Edge()


@pytest.mark.parametrize("suelta", [((-3, 0), (3, 0)), ((-10, 0), (0, 0))], ids=["libre", "pegada_al_borde"])
def test_silueta_sin_curvas_sueltas(monkeypatch, suelta):
    cuadrado = [_seg((-10, -10), (10, -10)), _seg((10, -10), (10, 10)), _seg((10, 10), (-10, 10)),
                _seg((-10, 10), (-10, -10))]
    monkeypatch.setattr(pf, "_hlr_exacto", lambda forma, plano: cuadrado + [_seg(*suelta)])
    prims, _ = pf._silueta(g.caja(20, 20, 5, (-10, -10, -5)), g.Plano("XY"), 1e-4, None)
    assert [p[0] for p in prims] == ["linea"] * 4
    assert all(abs(abs(x) - 10) < 1e-6 or abs(abs(y) - 10) < 1e-6 for p in prims for x, y in p[2:4])
