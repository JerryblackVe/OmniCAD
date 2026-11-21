"""B-619c: el Perfil giratorio del barril de dos tramos da arcos y pocas líneas (Fusion, a 0,01 mm: 5 líneas y 8 arcos),
no 23 rectas; y los arcos siguen la superficie del cuerpo."""
import math

import pytest

from omnicad import api


@pytest.fixture(scope="module")
def sesion():
    s = api.Sesion()

    def llamar(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, r)
        return r["result"]
    llamar("create_sketch", plane="XZ", name="Perfil")
    llamar("draw_line", start_x=0, start_y=0, end_x=30, end_y=0)
    llamar("draw_spline", points=[[30, 0], [35, 8], [38, 20], [38.5, 32], [36, 45]])
    llamar("draw_spline", points=[[36, 45], [39, 55], [40, 65], [37.5, 80], [32, 90]])
    llamar("draw_line", start_x=32, start_y=90, end_x=0, end_y=90)
    llamar("draw_line", start_x=0, start_y=90, end_x=0, end_y=0)
    llamar("revolve", sketch="Perfil", profile=0, axis="z")
    llamar("create_sketch", plane="XZ", name="Giro")
    llamar("project_spun_profile", axis="Z", bodies=["Cuerpo1"], tolerance=0.01, sketch="Giro")
    s.entidades = llamar("get_sketch", sketch="Giro")["entities"]
    return s


def test_el_barril_da_arcos_y_pocas_lineas(sesion):
    tipos = [e["type"] for e in sesion.entidades]
    assert tipos.count("arc") >= 4 and tipos.count("line") <= 5 and len(tipos) <= 16, tipos


def test_los_arcos_caen_sobre_la_superficie(sesion):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    forma = sesion.cuerpo("Cuerpo1").forma
    for e in (e for e in sesion.entidades if e["type"] == "arc"):
        a0, a1 = e["start_angle"], e["end_angle"]
        a1 += 360 if a1 < a0 else 0
        for k in range(11):
            ang = math.radians(a0 + (a1 - a0) * k / 10)
            u, v = e["center"][0] + e["radius"] * math.cos(ang), e["center"][1] + e["radius"] * math.sin(ang)
            d = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(u, 0, v)).Vertex(), forma).Value()
            assert d < 0.02, (e["id"], u, v, d)
