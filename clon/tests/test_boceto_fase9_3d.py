# -*- coding: utf-8 -*-
"""Fase 9 del Boceto 3D (FU-1 y BOC-18 3D): arco, círculo, elipse, rectángulo, cónica y texto 3D; concéntrica,
colineal, tangente spline–spline y cota angular 3D; mover/rotar/escalar/copiar lo 3D; Intersection Curve y
Project To Surface. Núcleo (restricciones.boceto3d) y API (MCP/CLI) con resultados numéricos."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import curvas3d
from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.restricciones import boceto3d as b3
from omnicad.restricciones.boceto import ErrorBoceto


def _xyz(b, pid):
    return np.array(b.geo3d["puntos"][pid], float)


def _largo(b, cid):
    return curvas3d.longitud(b3.arista(b, cid, geo.Plano("XY")))


def _tangente(arista, extremo):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    ad = BRepAdaptor_Curve(arista)
    t = ad.FirstParameter() if extremo == 0 else ad.LastParameter()
    d = ad.DN(t, 1)
    v = np.array([d.X(), d.Y(), d.Z()])
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------- núcleo: curvas nuevas
def test_arco_3d_de_tres_puntos_fuera_del_plano():
    b = Boceto()
    # cuarto de círculo de radio 10 en el plano XZ
    c = b3.agregar_arco(b, (10, 0, 0), (10 * math.cos(math.pi / 4), 0, 10 * math.sin(math.pi / 4)), (0, 0, 10))
    assert _largo(b, c) == pytest.approx(math.pi * 10 / 2, rel=1e-9)
    assert np.allclose(b3.centro(b, c), (0, 0, 0), atol=1e-9)
    with pytest.raises(ErrorBoceto, match="alineados"):
        b3.agregar_arco(b, (0, 0, 0), (1, 1, 1), (2, 2, 2))


def test_circulo_y_elipse_3d_en_un_plano_inclinado():
    b = Boceto()
    n = np.array([0.0, 1.0, 1.0]) / math.sqrt(2)
    c = b3.agregar_circulo(b, (1, 2, 3), 5, n)
    assert _largo(b, c) == pytest.approx(2 * math.pi * 5, rel=1e-9)
    muestras = curvas3d.muestrear(b3.arista(b, c, geo.Plano("XY")), 16)
    assert np.allclose((muestras - (1, 2, 3)) @ n, 0, atol=1e-5)          # el círculo vive en el plano de la normal
    e = b3.agregar_elipse(b, (0, 0, 0), (0, 0, 8), 3, (1, 0, 0))           # semieje mayor 8 sobre Z, menor 3
    a, m = 8, 3
    ramanujan = math.pi * (3 * (a + m) - math.sqrt((3 * a + m) * (a + 3 * m)))
    assert _largo(b, e) == pytest.approx(ramanujan, rel=1e-4)
    with pytest.raises(ErrorBoceto, match="perpendicular"):
        b3.agregar_elipse(b, (0, 0, 0), (0, 0, 8), 3, (0, 0, 1))


def test_rectangulo_3d_restringido_queda_rectangulo_al_resolver():
    b = Boceto()
    u, v = (1, 0, 0), (0, 0, 1)                                             # plano XZ
    lineas = b3.agregar_rectangulo(b, (0, 5, 0), (20, 5, 10), u, v)
    assert len(lineas) == 4
    assert sorted(round(_largo(b, c), 9) for c in lineas) == [10, 10, 20, 20]
    tipos = sorted(r["tipo"] for r in b.geo3d["restricciones"].values())
    assert tipos == ["paralela", "paralela", "perpendicular"]
    b3.agregar_cota(b, [lineas[0]], "30")                                    # se estira: sigue rectángulo
    assert b3.resolver(b, {k: 30.0 for k in b.geo3d["cotas"]}).ok
    p = [_xyz(b, b.geo3d["curvas"][c]["puntos"][0]) for c in lineas]
    lados = [p[(i + 1) % 4] - p[i] for i in range(4)]
    assert np.linalg.norm(lados[0]) == pytest.approx(30, abs=1e-6)
    assert abs(lados[0] @ lados[1]) < 1e-6 and np.allclose(lados[0], -lados[2], atol=1e-6)


def test_conica_3d_con_rho():
    b = Boceto()
    parabola = b3.agregar_conica(b, (0, 0, 0), (5, 0, 5), (10, 0, 0), 0.5)
    # rho = 0.5: parábola; su punto medio está a mitad de camino entre la cuerda y el vértice
    medio = curvas3d.muestrear(b3.arista(b, parabola, geo.Plano("XY")), 2)[1]
    assert np.allclose(medio, (5, 0, 2.5), atol=1e-6)
    with pytest.raises(ErrorBoceto, match="rho"):
        b3.agregar_conica(b, (0, 0, 0), (5, 0, 5), (10, 0, 0), 1.0)


def test_texto_3d_sobre_un_plano_vertical():
    b = Boceto()
    t = b3.agregar_texto(b, (0, 0, 0), "L", 10, (1, 0, 0), (0, 0, 1))      # texto parado en el plano XZ
    polis = b3.polilineas(b, geo.Plano("XY"))
    todos = np.vstack(polis)
    assert np.allclose(todos[:, 1], 0, atol=1e-6)                            # todo en y = 0
    assert 5 < todos[:, 2].max() <= 10.5 and todos[:, 0].min() >= -0.5       # alto de la letra a lo largo de z
    assert b.geo3d["curvas"][t]["texto"] == "L"
    with pytest.raises(ErrorBoceto):
        b3.agregar_texto(b, (0, 0, 0), "", 10, (1, 0, 0), (0, 0, 1))


# ---------------------------------------------------------------- núcleo: restricciones y cotas nuevas
def test_concentrica_arco_y_circulo():
    b = Boceto()
    arco = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    circ = b3.agregar_circulo(b, (3, 4, 5), 2, (0, 0, 1))
    b3.agregar_restriccion(b, "concentrica", [arco, circ])
    r = b3.resolver(b, {})
    assert r.ok
    assert np.allclose(b3.centro(b, arco), b3.centro(b, circ), atol=1e-6)
    with pytest.raises(ErrorBoceto):
        b3.agregar_restriccion(b, "concentrica", [arco, b3.agregar_linea(b, (0, 0, 0), (1, 1, 1))])


def test_colineal_dos_lineas_3d():
    b = Boceto()
    a = b3.agregar_linea(b, (0, 0, 0), (10, 10, 10))
    c = b3.agregar_linea(b, (0, 5, 20), (3, 7, 25))
    b3.agregar_restriccion(b, "fijo", [a])
    b3.agregar_restriccion(b, "colineal", [a, c])
    assert b3.resolver(b, {}).ok
    d = np.array([1, 1, 1]) / math.sqrt(3)
    for p in b.geo3d["curvas"][c]["puntos"]:
        q = _xyz(b, p)
        assert np.linalg.norm(np.cross(q, d)) < 1e-6                          # los dos extremos sobre la recta de a


def test_cota_angular_3d_entre_dos_lineas():
    b = Boceto()
    a = b3.agregar_linea(b, (0, 0, 0), (10, 0, 0))
    c = b3.agregar_linea(b, (0, 0, 0), (0, 10, 10))
    b3.agregar_restriccion(b, "fijo", [a])
    k = b3.agregar_cota(b, [a, c], "60", tipo="angulo")
    assert b3.resolver(b, {k: 60.0}).ok
    pa, pc = (b.geo3d["curvas"][x]["puntos"] for x in (a, c))
    da, dc = _xyz(b, pa[1]) - _xyz(b, pa[0]), _xyz(b, pc[1]) - _xyz(b, pc[0])
    angulo = math.degrees(math.acos(da @ dc / np.linalg.norm(da) / np.linalg.norm(dc)))
    assert angulo == pytest.approx(60, abs=1e-6)
    with pytest.raises(ErrorBoceto):
        b3.agregar_cota(b, [a], "30", tipo="angulo")
    assert not b3.resolver(b, {k: 0.0}).ok


def test_tangente_spline_spline_da_continuidad_g1():
    b = Boceto()
    s1 = b3.agregar_spline(b, [(0, 0, 0), (5, 5, 0), (10, 0, 5)])
    s2 = b3.agregar_spline(b, [(10, 0, 5), (15, -8, 5), (20, 0, 0)])
    plano = geo.Plano("XY")
    antes = abs(_tangente(b3.arista(b, s1, plano), -1) @ _tangente(b3.arista(b, s2, plano), 0))
    b3.agregar_restriccion(b, "tangente", [s1, s2])
    t1, t2 = _tangente(b3.arista(b, s1, plano), -1), _tangente(b3.arista(b, s2, plano), 0)
    assert antes < 0.99 and t1 @ t2 == pytest.approx(1, abs=1e-9)
    suelta = b3.agregar_spline(b, [(50, 0, 0), (60, 1, 1)])
    with pytest.raises(ErrorBoceto, match="extremo"):
        b3.agregar_restriccion(b, "tangente", [s1, suelta])


def test_transformar_mueve_rota_escala_y_copia():
    b = Boceto()
    linea = b3.agregar_linea(b, (0, 0, 0), (10, 0, 0))
    circ = b3.agregar_circulo(b, (0, 0, 0), 2, (0, 0, 1))
    giro = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)           # 90° alrededor de Y
    nuevos = b3.transformar(b, [linea, circ], 2 * giro, (0, 0, 5), (0, 0, 0), copiar=True)
    assert len(nuevos) == 2 and len(b.geo3d["curvas"]) == 4
    nl, nc = nuevos
    p0, p1 = (_xyz(b, p) for p in b.geo3d["curvas"][nl]["puntos"])
    assert np.allclose(p0, (0, 0, 5)) and np.allclose(p1, (0, 0, -15))   # largo 20 (escala 2), a lo largo de −Z
    assert b.geo3d["curvas"][nc]["radio"] == pytest.approx(4)
    assert np.allclose(b.geo3d["curvas"][nc]["normal"], (1, 0, 0))
    assert np.allclose(_xyz(b, b.geo3d["curvas"][linea]["puntos"][1]), (10, 0, 0))   # el original no se movió
    b3.transformar(b, [linea], np.identity(3), (1, 2, 3), (0, 0, 0))                    # mover sin copiar
    assert np.allclose(_xyz(b, b.geo3d["curvas"][linea]["puntos"][1]), (11, 2, 3))


def test_round_trip_de_las_curvas_nuevas():
    b = Boceto()
    b3.agregar_circulo(b, (0, 0, 1), 3, (0, 1, 0))
    b3.agregar_texto(b, (0, 0, 0), "A", 5, (1, 0, 0), (0, 1, 0))
    b3.agregar_conica(b, (0, 0, 0), (1, 1, 1), (2, 0, 0), 0.3)
    d = Boceto.desde_dict(b.a_dict())
    assert d.a_dict() == b.a_dict()


# ---------------------------------------------------------------- API
@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def falla(sesion, nombre, kind, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def _entidades(s, sketch=None):
    return {e["id"]: e for e in llamar(s, "get_sketch", **({"sketch": sketch} if sketch else {}))["entities_3d"]}


def test_api_dibuja_las_curvas_3d_nuevas(s):
    llamar(s, "create_sketch", plane="XY")
    arco = llamar(s, "draw_arc_3d", start=[10, 0, 0], through=[0, 0, 10], end=[-10, 0, 0])["entity"]
    circ = llamar(s, "draw_circle_3d", center=[0, 0, 20], radius=4, normal=[1, 0, 0])["entity"]
    elip = llamar(s, "draw_ellipse_3d", center=[0, 0, 0], major_end=[0, 6, 0], minor_radius=2,
                  normal=[0, 0, 1])["entity"]
    rect = llamar(s, "draw_rectangle_3d", corner=[0, 0, 5], opposite=[4, 9, 3], plane="xy")
    con = llamar(s, "draw_conic_3d", start=[0, 0, 0], shoulder=[5, 5, 5], end=[10, 0, 0], rho=0.4)["entity"]
    txt = llamar(s, "draw_text_3d", text="Hi", origin=[0, 0, 0], height=5, plane="zx")["entity"]
    e = _entidades(s)
    assert e[arco]["type"] == "arc" and e[arco]["length"] == pytest.approx(math.pi * 10, rel=1e-6)
    assert e[arco]["center"] == [0, 0, 0] and e[arco]["radius"] == 10
    assert e[circ]["type"] == "circle" and e[circ]["length"] == pytest.approx(8 * math.pi, rel=1e-5)
    assert e[elip]["type"] == "ellipse" and e[elip]["minor_radius"] == 2
    assert len(rect["entities"]) == 4
    assert {e[i]["end"][2] for i in rect["entities"]} == {5}                 # plano xy por la esquina: z = 5
    assert sorted(e[i]["length"] for i in rect["entities"]) == [4, 4, 9, 9]
    assert e[con]["type"] == "conic" and e[con]["rho"] == 0.4
    assert e[txt]["type"] == "text" and e[txt]["text"] == "Hi"


def test_api_restricciones_nuevas_y_cota_angular(s):
    llamar(s, "create_sketch", plane="XY")
    a = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[10, 0, 0])["entity"]
    c = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[0, 10, 0])["entity"]
    llamar(s, "add_constraint_3d", type="fix", entities=[a])
    llamar(s, "add_dimension_3d", entities=[a, c], value="30 deg", type="angle")
    e = _entidades(s)
    d = np.subtract(e[c]["end"], e[c]["start"])
    assert math.degrees(math.acos(d[0] / np.linalg.norm(d))) == pytest.approx(30, abs=1e-3)
    info = llamar(s, "get_sketch")
    (cota,) = info["dimensions_3d"]
    assert cota["type"] == "angle" and cota["value"] == pytest.approx(30)
    c1 = llamar(s, "draw_circle_3d", center=[1, 1, 1], radius=2)["entity"]
    c2 = llamar(s, "draw_circle_3d", center=[5, 5, 5], radius=3, normal=[0, 1, 0])["entity"]
    llamar(s, "add_constraint_3d", type="concentric", entities=[c1, c2])
    e = _entidades(s)
    assert np.allclose(e[c1]["center"], e[c2]["center"], atol=1e-3)
    l3 = llamar(s, "draw_line_3d", start=[20, 1, 0], end=[30, 2, 0])["entity"]
    llamar(s, "add_constraint_3d", type="collinear", entities=[a, l3])
    e = _entidades(s)
    assert abs(e[l3]["start"][1]) < 1e-3 and abs(e[l3]["end"][1]) < 1e-3
    falla(s, "add_dimension_3d", "INVALID_DIMENSION", entities=[a], value=30, type="angle")
    falla(s, "add_dimension_3d", "INVALID_EXPRESSION", entities=[a, c], value="5 mm", type="angle")


def test_api_tangente_spline_spline_y_barrido(s):
    llamar(s, "create_sketch", plane="XY", name="Ruta")
    linea = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[0, 0, 10])["entity"]       # arranca normal al perfil
    s1 = llamar(s, "draw_spline_3d", points=[[0, 0, 10], [5, 5, 20], [10, 0, 30]])["entity"]
    s2 = llamar(s, "draw_spline_3d", points=[[10, 0, 30], [12, -5, 40], [20, 0, 45]])["entity"]
    llamar(s, "add_constraint_3d", type="tangent", entities=[linea, s1])
    llamar(s, "add_constraint_3d", type="tangent", entities=[s1, s2])
    info = llamar(s, "get_sketch", sketch="Ruta")
    assert [r["type"] for r in info["constraints_3d"]] == ["tangent", "tangent"]
    llamar(s, "create_sketch", plane="XY", name="Perfil")
    llamar(s, "draw_circle", center_x=0, center_y=0, radius=1)
    llamar(s, "sweep", sketch="Perfil", profile=0, path_sketch="Ruta")
    (cuerpo,) = s.doc.estado_final.cuerpos.values()
    largo = sum(e["length"] for e in info["entities_3d"])
    assert geo.volumen(cuerpo.forma) == pytest.approx(math.pi * largo, rel=2e-2)


def test_api_transform_sketch_3d(s):
    llamar(s, "create_sketch", plane="XY")
    a = llamar(s, "draw_line_3d", start=[0, 0, 0], end=[10, 0, 0])["entity"]
    r = llamar(s, "transform_sketch_3d", entities=[a], rotation_axis=[0, 0, 1], rotation_angle=90, scale=0.5,
               translation=[0, 0, 7], copy=True)
    (nueva,) = r["entities"]
    e = _entidades(s)
    assert e[nueva]["start"] == [0, 0, 7] and e[nueva]["end"] == [0, 5, 7]
    assert e[a]["end"] == [10, 0, 0]
    falla(s, "transform_sketch_3d", "INVALID_ARGUMENTS", entities=[a], scale=0)
    falla(s, "transform_sketch_3d", "ENTITY_NOT_FOUND", entities=[999], translation=[1, 0, 0])


def test_api_intersect_curves_plano_inclinado_con_cilindro_da_elipse(s):
    llamar(s, "create_cylinder", radius=10, height=40, z=-20)
    plano = llamar(s, "create_construction_plane", type="angle", references=["X"], angle=45)["plane"]["id"]
    llamar(s, "create_sketch", plane="XY", name="Corte")
    r = llamar(s, "intersect_curves", faces=["%CYLINDER"], references=[plano])
    assert r["entities"]
    e = _entidades(s, "Corte")
    (elipse,) = [e[i] for i in r["entities"]]
    a, m = 10 * math.sqrt(2), 10
    ramanujan = math.pi * (3 * (a + m) - math.sqrt((3 * a + m) * (a + 3 * m)))
    assert elipse["length"] == pytest.approx(ramanujan, rel=1e-3)
    falla(s, "intersect_curves", "INVALID_ARGUMENTS", faces=["%CYLINDER"])


def test_api_intersect_curves_curva_de_boceto_contra_cara(s):
    """Fusion: la curva del boceto se extruye a lo largo de la normal de su plano y se corta con la cara."""
    llamar(s, "create_cylinder", radius=10, height=40)
    llamar(s, "create_sketch", plane="XZ", name="Guia")
    linea = llamar(s, "draw_line", start_x=-20, start_y=5, end_x=20, end_y=35)["entities"][0]["id"]
    llamar(s, "create_sketch", plane="XY", name="Curva3D")
    r = llamar(s, "intersect_curves", faces=["%CYLINDER"], curves=[{"sketch": "Guia", "curve": linea}])
    (curva,) = [_entidades(s, "Curva3D")[i] for i in r["entities"]]
    # el plano z = 20 + 0,75·x corta el cilindro de radio 10 en una elipse de semiejes 10 y 12,5
    assert curva["type"] == "ellipse" and curva["minor_radius"] == pytest.approx(10)
    assert np.linalg.norm(curva["major_axis"]) == pytest.approx(12.5) and curva["center"] == [0, 0, 20]


def test_api_project_to_surface_vector_y_cercano(s):
    llamar(s, "create_box", length=40, width=40, height=10)
    plano = llamar(s, "create_construction_plane", plane="XY", offset=30)["plane"]["id"]
    llamar(s, "create_sketch", plane=plano, name="Fuente")
    circ = llamar(s, "draw_circle", center_x=0, center_y=0, radius=5)["entities"][0]["id"]
    llamar(s, "create_sketch", plane="XY", name="Destino")
    r = llamar(s, "project_to_surface", faces=[">Z"], curves=[{"sketch": "Fuente", "curve": circ}],
               mode="vector", direction=[0, 0, -1])
    e = _entidades(s, "Destino")
    (c,) = [e[i] for i in r["entities"]]
    assert c["type"] == "circle" and c["radius"] == pytest.approx(5) and c["center"][2] == pytest.approx(10)
    r = llamar(s, "project_to_surface", faces=[">Z"], curves=[{"sketch": "Fuente", "curve": circ}], mode="closest")
    e = _entidades(s, "Destino")
    pts = np.vstack([np.array(e[i].get("vertices") or [e[i]["center"]]) for i in r["entities"]])
    assert np.allclose(pts[:, 2], 10, atol=1e-6)
    assert sum(e[i]["length"] for i in r["entities"]) == pytest.approx(10 * math.pi, rel=1e-3)
    falla(s, "project_to_surface", "INVALID_ARGUMENTS", faces=[">Z"], curves=[{"sketch": "Fuente", "curve": circ}],
          mode="vector")
