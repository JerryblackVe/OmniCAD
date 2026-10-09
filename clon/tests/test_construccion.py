# -*- coding: utf-8 -*-
import math

import numpy as np
import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder
from OCP.TopAbs import TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

from omnicad.nucleo import construccion as cn
from omnicad.nucleo import geometria as g

S2 = math.sqrt(0.5)


# ---------------------------------------------------------------- ayudas
def seg(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, b))).Edge()


def arco(r, a0, a1):
    return BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), r), a0, a1).Edge()


def cara_con_normal(solido, normal):
    for c in g.caras(solido):
        pl = g.plano_de_cara(c)
        if pl is not None and np.allclose(pl.normal, normal, atol=1e-9):
            return c
    raise AssertionError(f"no hay cara con normal {normal}")


def arista_en(forma, punto):
    for e in g._explorar(forma, TopAbs_EDGE):
        (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(e)
        if np.allclose([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], punto, atol=1e-6):
            return TopoDS.Edge(e)
    raise AssertionError(f"no hay arista en {punto}")


def lateral(solido):
    return next(c for c in g.caras(solido) if BRepAdaptor_Surface(c).GetType() == GeomAbs_Cylinder)


def paralelos(a, b):
    return abs(abs(float(np.dot(a, b))) - 1.0) < 1e-9


def en_plano(pl, p):
    return abs(float((np.asarray(p, float) - pl.origen) @ pl.normal)) < 1e-9


CAJA = g.caja(10, 10, 10)


# ---------------------------------------------------------------- conversiones
def test_conversiones():
    assert np.allclose(cn.punto_de((1, 2, 3)), (1, 2, 3))
    assert np.allclose(cn.punto_de(gp_Pnt(4, 5, 6)), (4, 5, 6))
    vertices = [TopoDS.Vertex(v) for v in g._explorar(CAJA, TopAbs_VERTEX)]
    assert any(np.allclose(cn.punto_vertice(v), (10, 10, 10)) for v in vertices)
    assert cn.plano_de("XZ").nombre == "XZ"
    assert np.allclose(cn.plano_de(cara_con_normal(CAJA, (0, 0, 1))).origen, (0, 0, 10))
    e = cn.eje_de(((0, 0, 0), (0, 0, 5)))
    assert isinstance(e, tuple) and np.allclose(e.direccion, (0, 0, 1))
    with pytest.raises(g.ErrorGeometria):
        cn.plano_de(lateral(g.cilindro(5, 10)))
    with pytest.raises(g.ErrorGeometria):
        cn.punto_de((1, 2))


# ---------------------------------------------------------------- planos
def test_plano_desfase():
    pl = cn.plano_desfase(cara_con_normal(CAJA, (0, 0, 1)), 5)
    assert np.allclose(pl.origen, (0, 0, 15)) and np.allclose(pl.normal, (0, 0, 1))
    assert np.allclose(cn.plano_desfase("XY", -3).origen, (0, 0, -3))


def test_plano_en_angulo():
    xz = cn.plano_en_angulo("XY", (0, 0, 0), (1, 0, 0), 90)
    ref = g.Plano("XZ")
    assert np.allclose(xz.normal, ref.normal) and np.allclose(xz.u, ref.u) and np.allclose(xz.origen, 0)
    # Por una arista de la caja: plano a 45° respecto de la cara superior, conteniendo la arista.
    arista = arista_en(CAJA, (5, 0, 10))
    pl = cn.plano_en_angulo(cara_con_normal(CAJA, (0, 0, 1)), arista, None, 45)
    assert en_plano(pl, (0, 0, 10)) and en_plano(pl, (10, 0, 10))
    assert abs(pl.normal[2]) == pytest.approx(S2) and abs(pl.normal[1]) == pytest.approx(S2)
    assert cn.plano_en_angulo("XY", (0, 0, 0), (1, 0, 0), 90, desfase=2).origen == pytest.approx((0, -2, 0))
    with pytest.raises(g.ErrorGeometria):
        cn.plano_en_angulo("XY", (0, 0, 0), (0, 0, 1), 30)


def test_plano_tangente():
    lat = lateral(g.cilindro(5, 10))
    pl = cn.plano_tangente(lat, 0)
    assert np.allclose(pl.normal, (1, 0, 0)) and np.allclose(pl.origen, (5, 0, 5))
    pl = cn.plano_tangente(lat, 90)
    assert np.allclose(pl.normal, (0, 1, 0)) and pl.origen[1] == pytest.approx(5)
    pl = cn.plano_tangente(lat, np.array([0.0, -20.0, 3.0]))
    assert np.allclose(pl.normal, (0, -1, 0)) and np.allclose(pl.origen, (0, -5, 3))
    pl = cn.plano_tangente(lat, 0, "XZ")   # referencia: normal de XZ = -Y
    assert np.allclose(pl.normal, (0, -1, 0))
    assert cn.plano_tangente(lat, 0, desfase=1).origen[0] == pytest.approx(6)
    with pytest.raises(g.ErrorGeometria):
        cn.plano_tangente(cara_con_normal(CAJA, (0, 0, 1)), 0)


def test_plano_medio():
    pl = cn.plano_medio(cara_con_normal(CAJA, (0, 0, -1)), cara_con_normal(CAJA, (0, 0, 1)))
    assert pl.origen[2] == pytest.approx(5) and paralelos(pl.normal, (0, 0, 1))
    pl = cn.plano_medio(cara_con_normal(CAJA, (1, 0, 0)), cara_con_normal(CAJA, (0, 1, 0)))
    # Caras x=10 e y=10: bisector que cruza el material = plano diagonal x = y.
    assert en_plano(pl, (0, 0, 0)) and en_plano(pl, (10, 10, 3)) and paralelos(pl.normal, (S2, -S2, 0))


def test_plano_dos_aristas_y_tres_puntos():
    pl = cn.plano_dos_aristas(arista_en(CAJA, (5, 0, 0)), arista_en(CAJA, (5, 10, 10)))   # paralelas opuestas
    assert en_plano(pl, (0, 0, 0)) and en_plano(pl, (10, 10, 10)) and paralelos(pl.normal, (0, S2, -S2))
    pl = cn.plano_dos_aristas(arista_en(CAJA, (5, 0, 0)), arista_en(CAJA, (0, 5, 0)))
    assert paralelos(pl.normal, (0, 0, 1)) and en_plano(pl, (0, 0, 0))
    with pytest.raises(g.ErrorGeometria):
        cn.plano_dos_aristas(arista_en(CAJA, (5, 0, 0)), arista_en(CAJA, (0, 10, 5)))   # se cruzan sin cortarse
    pl = cn.plano_tres_puntos((10, 0, 0), (0, 10, 0), (0, 0, 10))
    assert paralelos(pl.normal, np.ones(3) / math.sqrt(3)) and en_plano(pl, (10 / 3, 10 / 3, 10 / 3))
    with pytest.raises(g.ErrorGeometria):
        cn.plano_tres_puntos((0, 0, 0), (1, 1, 1), (2, 2, 2))


def test_plano_perpendicular():
    pl = cn.plano_perpendicular(seg((0, 0, 0), (0, 0, 10)), (2, 0, 3))
    assert np.allclose(pl.normal, (0, 0, 1)) and np.allclose(pl.origen, (0, 0, 3))
    superior = cara_con_normal(CAJA, (0, 0, 1))
    pl = cn.plano_perpendicular(superior, (5, 5, 10))
    assert np.allclose(pl.normal, g.plano_de_cara(superior).u) and np.allclose(pl.origen, (5, 5, 10))
    assert paralelos(cn.plano_perpendicular(superior, (5, 5, 10), direccion="V").normal, g.plano_de_cara(superior).v)
    lat = lateral(g.cilindro(5, 10))
    u = cn.plano_perpendicular(lat, (5, 0, 4))   # U = circunferencial → plano radial y = 0
    assert paralelos(u.normal, (0, 1, 0)) and np.allclose(u.origen, (5, 0, 4))
    v = cn.plano_perpendicular(lat, (5, 0, 4), direccion="V")   # V = axial → plano z = 4
    assert paralelos(v.normal, (0, 0, 1)) and v.origen[2] == pytest.approx(4)


def test_plano_y_punto_en_ruta():
    pl = cn.plano_en_ruta([seg((0, 0, 0), (10, 0, 0))], 0.5)
    assert np.allclose(pl.origen, (5, 0, 0)) and np.allclose(pl.normal, (1, 0, 0))
    cuarto = arco(10, 0, math.pi / 2)
    pl = cn.plano_en_ruta(cuarto, 0.5)
    assert np.allclose(pl.origen, (10 * S2, 10 * S2, 0)) and np.allclose(pl.normal, (-S2, S2, 0))
    # Cadena de dos tramos (largo 20): 0.75 cae en el segundo; absoluta y pasado del final.
    cadena = [seg((10, 0, 0), (10, 10, 0)), seg((0, 0, 0), (10, 0, 0))]
    assert np.allclose(cn.punto_en_ruta(cadena, 0.75), (10, 5, 0))
    assert np.allclose(cn.punto_en_ruta(cadena, 3, absoluta=True), (3, 0, 0))
    assert np.allclose(cn.punto_en_ruta(cadena, 1.1), (10, 12, 0))


# ---------------------------------------------------------------- ejes
def test_eje_cilindro_cono_toroide():
    e = cn.eje_cilindro(lateral(g.cilindro(5, 10, base=(3, 4, 0))))
    assert np.allclose(e.punto, (3, 4, 5)) and paralelos(e.direccion, (0, 0, 1))
    cono = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), 5, 2, 6).Shape()
    lat_cono = next(c for c in g.caras(cono) if BRepAdaptor_Surface(c).GetType() == GeomAbs_Cone)
    e = cn.eje_cilindro(lat_cono)
    assert paralelos(e.direccion, (0, 1, 0)) and np.allclose(e.punto[[0, 2]], 0)
    assert np.allclose(cn.plano_tangente(lat_cono, np.array([20.0, 3.0, 0.0])).normal,
                       (6 / math.hypot(6, 3), 3 / math.hypot(6, 3), 0))   # generatriz con pendiente 3/6
    tor = cn.eje_cilindro(g.caras(g.toroide(10, 2, eje=(1, 0, 0)))[0])
    assert paralelos(tor.direccion, (1, 0, 0)) and np.allclose(tor.punto, 0, atol=1e-9)
    with pytest.raises(g.ErrorGeometria):
        cn.eje_cilindro(cara_con_normal(CAJA, (0, 0, 1)))


def test_eje_perpendicular_dos_planos_dos_puntos_arista():
    e = cn.eje_perpendicular_cara(cara_con_normal(CAJA, (0, 0, 1)), (3, 4, 50))
    assert np.allclose(e.punto, (3, 4, 10)) and np.allclose(e.direccion, (0, 0, 1))
    e = cn.eje_perpendicular_cara(lateral(g.cilindro(5, 10)), (10, 0, 2))
    assert np.allclose(e.punto, (5, 0, 2)) and np.allclose(e.direccion, (1, 0, 0))
    x = cn.eje_dos_planos("XY", "XZ")
    assert np.allclose(x.punto, 0) and paralelos(x.direccion, (1, 0, 0))
    e = cn.eje_dos_planos(cara_con_normal(CAJA, (0, 0, 1)), cara_con_normal(CAJA, (1, 0, 0)))
    assert np.allclose(e.punto, (10, 0, 10)) and paralelos(e.direccion, (0, 1, 0))
    with pytest.raises(g.ErrorGeometria):
        cn.eje_dos_planos("XY", cn.plano_desfase("XY", 3))
    e = cn.eje_dos_puntos((1, 1, 1), (1, 1, 4))
    assert np.allclose(e.direccion, (0, 0, 1))
    e = cn.eje_arista(seg((2, 0, 0), (2, 0, -6)))
    assert np.allclose(e.punto, (2, 0, 0)) and np.allclose(e.direccion, (0, 0, -1))
    with pytest.raises(g.ErrorGeometria):
        cn.eje_arista(arco(5, 0, 1))


# ---------------------------------------------------------------- puntos
def test_punto_tres_planos_y_arista_plano():
    assert np.allclose(cn.punto_tres_planos("XY", "XZ", "YZ"), 0)
    p = cn.punto_tres_planos(cara_con_normal(CAJA, (0, 0, 1)), cara_con_normal(CAJA, (1, 0, 0)),
                             cara_con_normal(CAJA, (0, 1, 0)))
    assert np.allclose(p, (10, 10, 10))
    with pytest.raises(g.ErrorGeometria):
        cn.punto_tres_planos("XY", cn.plano_desfase("XY", 1), "YZ")
    assert np.allclose(cn.punto_arista_plano(seg((1, 2, 3), (1, 2, 4)), "XY"), (1, 2, 0))   # prolongada
    with pytest.raises(g.ErrorGeometria):
        cn.punto_arista_plano(seg((0, 0, 1), (1, 0, 1)), "XY")


def test_punto_dos_aristas():
    assert np.allclose(cn.punto_dos_aristas(seg((0, 0, 0), (1, 0, 0)), seg((5, 3, 0), (5, 4, 0))), (5, 0, 0))
    # Rectas que se cruzan sin cortarse (z=0 y z=2): punto medio de la perpendicular común.
    assert np.allclose(cn.punto_dos_aristas(seg((0, 0, 0), (1, 0, 0)), seg((0, 0, 2), (0, 1, 2))), (0, 0, 1))
    p = cn.punto_dos_aristas(arco(10, 0, math.pi), seg((0, -5, 0), (0, 15, 0)))
    assert np.allclose(p, (0, 10, 0), atol=1e-6)
    with pytest.raises(g.ErrorGeometria):
        cn.punto_dos_aristas(seg((0, 0, 0), (1, 0, 0)), seg((0, 1, 0), (1, 1, 0)))


def test_punto_centro():
    assert np.allclose(cn.punto_centro(arco(7, 0, 1)), 0)
    assert np.allclose(cn.punto_centro(g.caras(g.esfera(3, (1, 2, 3)))[0]), (1, 2, 3))
    assert np.allclose(cn.punto_centro(g.caras(g.toroide(10, 2, (0, 0, 5)))[0]), (0, 0, 5))
    tapa = cara_con_normal(g.cilindro(5, 10, base=(3, 4, 0)), (0, 0, 1))
    assert np.allclose(cn.punto_centro(tapa), (3, 4, 10))
    with pytest.raises(g.ErrorGeometria):
        cn.punto_centro(cara_con_normal(CAJA, (0, 0, 1)))


# ---------------------------------------------------------------- SCU
def test_scu():
    m = cn.scu((1, 2, 3), (2, 0, 0), (1, 5, 0))
    assert np.allclose(m["x"], (1, 0, 0)) and np.allclose(m["y"], (0, 1, 0)) and np.allclose(m["z"], (0, 0, 1))
    assert np.allclose(m["matriz"] @ np.array([1, 0, 0, 1.0]), (2, 2, 3, 1))
    m = cn.scu((0, 0, 0), seg((0, 0, 0), (0, 3, 0)), (0, 0, 1))   # X por una arista
    assert np.allclose(m["x"], (0, 1, 0)) and np.allclose(m["z"], (1, 0, 0))
    m = cn.scu((0, 0, 0), (1, 0, 0), (0, 1, 0), angulos=(0, 0, 90), desfase=(0, 0, 4))
    assert np.allclose(m["x"], (0, 1, 0)) and np.allclose(m["y"], (-1, 0, 0)) and np.allclose(m["origen"], (0, 0, 4))
    assert np.allclose(m["plano"].normal, (0, 0, 1)) and np.isclose(np.linalg.det(m["matriz"][:3, :3]), 1)
    with pytest.raises(g.ErrorGeometria):
        cn.scu((0, 0, 0), (1, 0, 0), (3, 0, 0))
