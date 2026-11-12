"""B-173: la solevación de 3 splines cerrados (antebrazo del brazo robótico, 86 puntos cada uno) salía `ok` plegada
(1,87 L en vez de ~4 L; con el orden invertido, volumen negativo) y `check_geometry` la daba por válida con una
autointersección de severidad error. Los puntos son los de los bocetos del documento original."""
import json
from pathlib import Path

import pytest

from omnicad import api
from omnicad.nucleo import revision as rv

PUNTOS = json.loads((Path(__file__).parent / "datos" / "b173_secciones_antebrazo.json").read_text(encoding="utf-8"))


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, r)
    return r["result"]


def _secciones():
    s = api.Sesion()
    _llamar(s, "create_construction_plane", plane="XZ", offset=-41, name="Pl_Y_p41")
    _llamar(s, "create_construction_plane", plane="XZ", offset=41, name="Pl_Y_n41")
    for boceto, plano in (("Bc_ant_p", "Pl_Y_p41"), ("Bc_ant_m", "XZ"), ("Bc_ant_n", "Pl_Y_n41")):
        _llamar(s, "sketch_from_spec", name=boceto, plane=plano,
                entities=[{"type": "spline", "points": PUNTOS[boceto], "closed": True, "spline_type": "fit_points"}])
    return s


@pytest.mark.parametrize("orden", [["Bc_ant_n", "Bc_ant_m", "Bc_ant_p"], ["Bc_ant_p", "Bc_ant_m", "Bc_ant_n"]])
def test_la_solevacion_no_se_pliega_y_no_depende_del_orden(orden):
    s = _secciones()

    r = _llamar(s, "loft", sketches=orden, operation="new_body")

    volumen = r["bodies_created"][0]["volume"]
    assert volumen == pytest.approx(3.986e6, rel=0.01)          # antes: 1,87e6 en un orden y negativo en el otro
    g = _llamar(s, "check_geometry", body=r["bodies_created"][0]["id"])["bodies"][0]
    assert g["valid"] and g["self_intersections"] == 0


def test_revisar_marca_invalida_una_autointerseccion():
    """La solevación plegada tal como la armaba el kernel con su ajuste de compatibilidad: BRepCheck la da por buena."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS

    from omnicad.timeline.operaciones import _resolver_todas
    s = _secciones()
    paso = _llamar(s, "loft", sketches=["Bc_ant_n", "Bc_ant_m"], operation="new_body")["feature"]["id"]
    ts = BRepOffsetAPI_ThruSections(True, False)       # con el ajuste de compatibilidad, como antes del arreglo
    for seccion in _resolver_todas(s.paso(paso).p["secciones"], s.doc.estado_final):
        ts.AddWire(BRepTools.OuterWire_s(TopoDS.Face(seccion.forma)))
    ts.Build()

    informe = rv.revisar(ts.Shape())

    assert informe["autointersecciones"] and informe["errores"]
    assert not informe["valido"]


def test_b172_propiedades_de_la_solevacion_sobre_malla_vacia_no_integran_la_malla(monkeypatch):
    """B-172: pedir las propiedades de una solevación de splines cerró la app (violación de acceso en TKernel dentro de
    `geometria._por_malla`, que integra sobre la malla). No se repite con solevaciones variadas (60 en bucle, procesos
    aparte), así que el guardia es la defensa: una cara con malla vacía no se integra y vale la integración exacta."""
    from omnicad.nucleo import geometria as geo
    s = _secciones()
    forma = s.cuerpo(_llamar(s, "loft", sketches=["Bc_ant_n", "Bc_ant_m", "Bc_ant_p"],
                             operation="new_body")["bodies_created"][0]["id"]).forma
    assert geo.es_forma_libre(forma)
    esperado = geo.volumen(forma)
    assert geo._por_malla(forma, geo.BRepGProp.VolumeProperties_s, 1e-3, True) == pytest.approx(esperado, rel=0.02)

    class _Vacia:
        def NbTriangles(self):
            return 0

        def NbNodes(self):
            return 0
    monkeypatch.setattr(geo.BRep_Tool, "Triangulation_s", staticmethod(lambda *a: _Vacia()))
    assert geo._por_malla(forma, geo.BRepGProp.VolumeProperties_s, 1e-3, True) is None
    assert geo.volumen(forma) == pytest.approx(esperado, rel=1e-9)     # sin malla, queda la integración exacta
