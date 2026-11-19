"""B-619b: Include 3D Geometry y Curva isoparamétrica copian la arista B-spline exacta del barril (5 polos del
perfil) como spline de puntos de control, en vez de remuestrearla a 33 puntos de ajuste (`curvas3d.describir`)."""
import pytest

from omnicad import api
from omnicad.nucleo import curvas3d, geometria as geo
from omnicad.restricciones import boceto3d as b3
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.GeomAbs import GeomAbs_BSplineCurve
from OCP.gp import gp_Pnt

POCOS = 10       # el perfil del barril tiene 5 polos; 33 era el remuestreo de antes
TOL = 1e-3       # mm: la copia exacta da ~5e-5; guardar los polos como puntos de ajuste da 1,35 mm


def _llamar(s, nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, r)
    return r["result"]


@pytest.fixture
def barril():
    """Barril de dos tramos del B-619: cada meridiano es una B-spline de 5 polos."""
    s = api.Sesion()
    for nombre, args in (
        ("create_sketch", {"plane": "XZ", "name": "Perfil"}),
        ("draw_line", {"start_x": 0, "start_y": 0, "end_x": 30, "end_y": 0}),
        ("draw_spline", {"points": [[30, 0], [35, 8], [38, 20], [38.5, 32], [36, 45]]}),
        ("draw_spline", {"points": [[36, 45], [39, 55], [40, 65], [37.5, 80], [32, 90]]}),
        ("draw_line", {"start_x": 32, "start_y": 90, "end_x": 0, "end_y": 90}),
        ("draw_line", {"start_x": 0, "start_y": 90, "end_x": 0, "end_y": 0}),
        ("revolve", {"sketch": "Perfil", "profile": 0, "axis": "z"}),
    ):
        _llamar(s, nombre, **args)
    return s


def _meridianos(s):
    """Aristas B-spline del barril (los dos meridianos del perfil girado)."""
    return [a for a in geo._aristas_unicas(s.cuerpo("Cuerpo1").forma)
            if BRepAdaptor_Curve(a).GetType() == GeomAbs_BSplineCurve]


def _distancia(shape, punto):
    return BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, punto))).Vertex(), shape).Value()


def _comprobar(s, sketch, cantidad):
    """Las curvas incluidas conservan 5 polos y siguen sobre el meridiano exacto."""
    exactos = _meridianos(s)
    assert len(exactos) == 2 and all(BRepAdaptor_Curve(a).BSpline().NbPoles() == 5 for a in exactos)
    spl = [e for e in _llamar(s, "get_sketch", sketch=sketch)["entities_3d"] if e["type"] == "spline"]
    assert len(spl) == cantidad
    assert max(len(e["points"]) for e in spl) <= POCOS              # antes: 33 puntos por curva
    assert all(e["spline_type"] == "control_points" and e["degree"] >= 3 for e in spl)   # la API dice que son polos
    b = s.paso(sketch).boceto
    for e in spl:
        ard = b3.arista(b, e["id"], geo.Plano("XY"))
        desvio = min(max(_distancia(ard, p) for p in curvas3d.muestrear(ex, 60)) for ex in exactos)
        assert desvio < TOL                                         # evita el atajo de polos como puntos de ajuste


def test_include_3d_geometry_copia_los_polos_del_meridiano(barril):
    s = barril
    _llamar(s, "create_sketch", plane="XY", name="Inc")
    ids = [e["id"] for e in _llamar(s, "find_edges", body="Cuerpo1")["edges"] if e["type"] == "bspline"]
    _llamar(s, "include_3d_geometry", edges=ids, body="Cuerpo1", sketch="Inc", link=False)
    _comprobar(s, "Inc", 2)


def test_isoparametric_curve_copia_los_polos_del_meridiano(barril):
    s = barril
    _llamar(s, "create_sketch", plane="XY", name="Iso")
    caras = [f["id"] for f in _llamar(s, "find_faces", body="Cuerpo1")["faces"] if f["type"] == "other"]
    _llamar(s, "isoparametric_curve", face=caras[0], point=[38, 0, 20], direction="v",
            body="Cuerpo1", sketch="Iso", link=False)
    _comprobar(s, "Iso", 1)


def _incluir_vinculado(s):
    _llamar(s, "create_sketch", plane="XY", name="Inc")
    ids = [e["id"] for e in _llamar(s, "find_edges", body="Cuerpo1")["edges"] if e["type"] == "bspline"]
    _llamar(s, "include_3d_geometry", edges=ids, body="Cuerpo1", sketch="Inc")
    return [e for e in _llamar(s, "get_sketch", sketch="Inc")["entities_3d"] if e["type"] == "spline"]


def test_con_vinculo_recalcula_la_spline_exacta_sin_aviso(barril):
    """El recálculo (`_seguir_al_modelo`) copia polos, nudos y grado de la arista: sin aviso de «cambió de forma»."""
    s = barril
    antes = _incluir_vinculado(s)
    s.doc.recalcular()
    mensajes = [r.mensaje for r in s.doc.resultados]
    assert not any("curva 3D" in m or "cambió de forma" in m for m in mensajes), mensajes
    _comprobar(s, "Inc", 2)
    assert [e["points"] for e in _llamar(s, "get_sketch", sketch="Inc")["entities_3d"] if e["type"] == "spline"] \
        == [e["points"] for e in antes]


def test_un_boceto_guardado_antes_conserva_su_spline_de_ajuste(barril):
    """Un boceto de antes de B-619b guarda la arista como spline de ajuste de 33 puntos: al recalcular la conserva
    (misma cantidad de puntos, sin aviso) en vez de perder el vínculo por el cambio de formato."""
    s = barril
    _incluir_vinculado(s)
    b = s.paso("Inc").boceto
    g = b3.datos(b)
    for cid, c in [(k, v) for k, v in g["curvas"].items() if "nudos" in v]:          # el formato de antes
        desc = curvas3d.como_ajuste({"tipo": "spline", "puntos": [b3.a_mundo(geo.Plano("XY"), g["puntos"][p])
                                                                  for p in c["puntos"]],
                                     "nudos": c["nudos"], "grado": c["grado"], "pesos": c["pesos"]})
        origen = c["origen"]
        b3.borrar(b, [cid])
        b3.agregar_desde_mundo(b, desc, geo.Plano("XY"), origen=origen)
    s.doc.recalcular()                                                               # como al abrir el archivo
    mensajes = [r.mensaje for r in s.doc.resultados]
    assert not any("cambió de forma" in m for m in mensajes), mensajes
    spl = [e for e in _llamar(s, "get_sketch", sketch="Inc")["entities_3d"] if e["type"] == "spline"]
    assert [len(e["points"]) for e in spl] == [33, 33]
    assert not any("nudos" in c for c in b3.datos(s.paso("Inc").boceto)["curvas"].values())
