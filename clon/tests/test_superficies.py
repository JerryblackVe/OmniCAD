# -*- coding: utf-8 -*-
import math

import numpy as np
import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pln, gp_Pnt

from omnicad.nucleo import geometria as g
from omnicad.nucleo import superficies as sf


# ---------------------------------------------------------------- ayudas
def seg(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, b))).Edge()


def circulo(r, centro=(0, 0, 0), normal=(0, 0, 1)):
    return BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(*map(float, centro)), gp_Dir(*map(float, normal))), r)).Edge()


def cuadrado(lado=10.0, z=0.0):
    p = [(0, 0, z), (lado, 0, z), (lado, lado, z), (0, lado, z)]
    return [seg(p[i], p[(i + 1) % 4]) for i in range(4)]


def cara_cuadrada(lado=10.0):
    return BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 0, lado, 0, lado).Face()


def aristas(forma):
    return [TopoDS.Edge(e) for e in g._explorar(forma, TopAbs_EDGE)]


def arista_en(forma, punto):
    """Arista de la forma cuyo punto medio de caja envolvente coincide con `punto`."""
    for e in aristas(forma):
        (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(e)
        if np.allclose([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], punto, atol=1e-6):
            return e
    raise AssertionError(f"no hay arista en {punto}")


def lateral(solido):
    return next(c for c in g.caras(solido) if BRepAdaptor_Surface(c).GetType() == GeomAbs_Cylinder)


# ---------------------------------------------------------------- crear
def test_extruir_linea_y_simetrica():
    s = sf.extruir_superficie(seg((0, 0, 0), (10, 0, 0)), (0, 0, 1), 5)
    assert g.area(s) == pytest.approx(50) and g.es_valida(s)
    s = sf.extruir_superficie(seg((0, 0, 0), (10, 0, 0)), (0, 0, 1), 8, simetrica=True)
    (_, _, z0), (_, _, z1) = g.caja_envolvente(s)
    assert (z0, z1) == pytest.approx((-4, 4)) and g.area(s) == pytest.approx(80)
    s = sf.extruir_superficie(cuadrado(), (0, 0, 1), -3)   # las 4 aristas se encadenan solas
    assert g.area(s) == pytest.approx(120) and g.caja_envolvente(s)[0][2] == pytest.approx(-3)


def test_extruir_con_conicidad():
    a = math.radians(5)
    afuera = sf.extruir_superficie(cuadrado(), (0, 0, 1), 10, conicidad=5)
    (x0, _, z0), (x1, _, z1) = g.caja_envolvente(afuera)
    assert (z0, z1) == pytest.approx((0, 10), abs=1e-6)
    assert x0 == pytest.approx(-10 * math.tan(a), abs=1e-6) and x1 == pytest.approx(10 + 10 * math.tan(a), abs=1e-6)
    lado_medio = 10 + 10 * math.tan(a)
    assert g.area(afuera) == pytest.approx(4 * lado_medio * 10 / math.cos(a), rel=1e-6)
    adentro = sf.extruir_superficie(cuadrado(), (0, 0, 1), 10, conicidad=-5)
    (x0, _, _), (x1, _, _) = g.caja_envolvente(adentro)
    assert x0 == pytest.approx(0, abs=1e-6) and x1 == pytest.approx(10, abs=1e-6)
    assert g.es_valida(afuera) and g.es_valida(adentro)


def test_revolver_linea_paralela_da_cilindro():
    s = sf.revolver_superficie(seg((5, 0, 0), (5, 0, 10)), (0, 0, 0), (0, 0, 1), 360)
    assert g.area(s) == pytest.approx(2 * math.pi * 5 * 10) and g.es_valida(s)
    media = sf.revolver_superficie(seg((5, 0, 0), (5, 0, 10)), (0, 0, 0), (0, 0, 1), 180)
    assert g.area(media) == pytest.approx(math.pi * 5 * 10)
    with pytest.raises(g.ErrorGeometria):
        sf.revolver_superficie(seg((5, 0, 0), (5, 0, 10)), (0, 0, 0), (0, 0, 1), 0)


def test_barrer_recto_paralelo_y_con_torsion():
    ruta = seg((0, 0, 0), (0, 0, 100))
    s = sf.barrer_superficie(seg((-5, 0, 0), (5, 0, 0)), ruta)
    assert g.area(s) == pytest.approx(1000) and g.es_valida(s)
    tubo = sf.barrer_superficie(circulo(3), ruta, orientacion="paralela")
    assert g.area(tubo) == pytest.approx(2 * math.pi * 3 * 100)
    # Torsión de 90°: helicoide de radio 5 → área = 2·∫₀⁵ 100·√(1+(k r)²) dr con k = (π/2)/100.
    k = (math.pi / 2) / 100
    n = 2000
    exacta = 2 * sum(100 * math.sqrt(1 + (k * (i + 0.5) * 5 / n) ** 2) * 5 / n for i in range(n))
    hel = sf.barrer_superficie(seg((-5, 0, 0), (5, 0, 0)), ruta, torsion=90)
    assert g.area(hel) == pytest.approx(exacta, rel=1e-4) and g.es_valida(hel)
    corte = BRepAlgoAPI_Section(hel, gp_Pln(gp_Pnt(0, 0, 50), gp_Dir(0, 0, 1))).Shape()
    (x0, y0, _), (x1, y1, _) = g.caja_envolvente(corte)
    assert (x1, y1) == pytest.approx((5 / math.sqrt(2), 5 / math.sqrt(2)), abs=1e-3)   # a mitad: 45°
    with pytest.raises(g.ErrorGeometria):
        sf.barrer_superficie(seg((-5, 0, 0), (5, 0, 0)), ruta, orientacion="paralela", torsion=30)


def test_barrer_ruta_curva():
    ruta = BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 50), 0, math.pi / 2).Edge()
    perfil = circulo(2, centro=(50, 0, 0), normal=(0, 1, 0))
    tubo = sf.barrer_superficie(perfil, ruta)
    assert g.area(tubo) == pytest.approx(2 * math.pi * 2 * (math.pi / 2 * 50), rel=1e-5) and g.es_valida(tubo)


def test_solevar_lineas_circulos_punto_y_cerrado():
    s = sf.solevar_superficie([seg((0, 0, 0), (10, 0, 0)), seg((0, 5, 0), (10, 5, 0))])
    assert g.area(s) == pytest.approx(50)
    cil = sf.solevar_superficie([circulo(5), circulo(5, (0, 0, 10))])
    assert g.area(cil) == pytest.approx(2 * math.pi * 50, rel=1e-6)
    cono = sf.solevar_superficie([circulo(5), np.array([0.0, 0.0, 12.0])])
    assert g.area(cono) == pytest.approx(math.pi * 5 * 13, rel=1e-4) and g.es_valida(cono)
    # Tres tramos verticales en un triángulo 3-4-5, reglado y cerrado: prisma lateral 10·(3+4+5).
    tramos = [seg((0, 0, 0), (0, 0, 10)), seg((4, 0, 0), (4, 0, 10)), seg((0, 3, 0), (0, 3, 10))]
    pr = sf.solevar_superficie(tramos, cerrada=True, reglada=True)
    assert g.area(pr) == pytest.approx(120) and g.es_valida(pr)
    with pytest.raises(g.ErrorGeometria):
        sf.solevar_superficie([seg((0, 0, 0), (1, 0, 0))])


def test_parche_plano_relleno_y_g1():
    p = sf.parche(cuadrado())
    assert g.area(p) == pytest.approx(100) and BRepAdaptor_Surface(p).GetType() == GeomAbs_Plane
    pts = [(0, 0, 0), (10, 0, 2), (10, 10, 0), (0, 10, 2)]
    alabeado = sf.parche([seg(pts[i], pts[(i + 1) % 4]) for i in range(4)])
    assert 100 < g.area(alabeado) < 103 and g.es_valida(alabeado)
    cil = g.cilindro(5, 10)
    lat = lateral(cil)
    borde = arista_en(lat, (0, 0, 10))
    c0 = sf.parche(borde, interior=[(0, 0, 15)])
    g1 = sf.parche(borde, continuidad="G1", interior=[(0, 0, 15)], soporte=lat)
    assert g.caja_envolvente(g1)[1][2] == pytest.approx(15, abs=1e-2)
    assert g.area(g1) > g.area(c0) > math.pi * 25    # G1 sale tangente a la pared: cúpula más llena
    assert g.es_valida(g1)
    with pytest.raises(g.ErrorGeometria):
        sf.parche(borde, continuidad="G1")


def test_reglada_tipos_y_angulo():
    cara = cara_cuadrada()
    borde = arista_en(cara, (5, 0, 0))
    n = sf.reglada(borde, 5, referencia=cara)
    assert g.area(n) == pytest.approx(50)
    assert g.caja_envolvente(n)[1][2] == pytest.approx(5)
    t = sf.reglada(borde, 5, tipo="tangente", referencia=cara)
    (_, y0, z0), (_, y1, z1) = g.caja_envolvente(t)
    assert (y0, y1) == pytest.approx((-5, 0), abs=1e-6) and z1 - z0 == pytest.approx(0, abs=1e-6)
    d = sf.reglada(borde, 5, tipo="direccion", direccion=(0, 0, -1))
    assert g.caja_envolvente(d)[0][2] == pytest.approx(-5)
    a = sf.reglada(borde, 5, 45, referencia=cara)
    assert g.area(a) == pytest.approx(50) and g.caja_envolvente(a)[1][2] == pytest.approx(5 / math.sqrt(2))
    # Normal girada 90° = tangente hacia afuera.
    a90 = sf.reglada(borde, 5, 90, referencia=cara)
    assert g.caja_envolvente(a90)[0][1] == pytest.approx(-5)


def test_reglada_sobre_borde_curvo():
    lat = lateral(g.cilindro(5, 10))
    corona = sf.reglada(arista_en(lat, (0, 0, 10)), 2, referencia=lat)   # normal radial: anillo plano
    assert g.area(corona) == pytest.approx(math.pi * (49 - 25), rel=1e-4) and g.es_valida(corona)
    assert g.caja_envolvente(corona)[1][0] == pytest.approx(7, abs=1e-3)


def test_desfasar_superficie():
    s = sf.desfasar_superficie(cara_cuadrada(), 3)
    assert g.area(s) == pytest.approx(100) and g.caja_envolvente(s)[0][2] == pytest.approx(3)
    c = sf.desfasar_superficie(lateral(g.cilindro(5, 10)), 2)
    assert g.area(c) == pytest.approx(2 * math.pi * 7 * 10)


def test_primitiva_superficie():
    for solido, area in ((g.caja(10, 20, 30), 2 * (200 + 300 + 600)), (g.esfera(5), 4 * math.pi * 25)):
        c = sf.primitiva_superficie(solido)
        assert g.area(c) == pytest.approx(area) and not g.solidos(c) and g.es_valida(c)


def test_empalme_y_chaflan_en_cascaron():
    f1 = cara_cuadrada()
    f2 = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, -1, 0)), 0, 10, 0, 10).Face()
    cas = sf.coser([f1, f2], 1e-6)["forma"]
    comun = arista_en(cas, (5, 0, 0))
    e = sf.empalme_superficie(cas, [comun], 2)
    assert g.area(e) == pytest.approx(160 + math.pi / 2 * 2 * 10) and g.es_valida(e)
    c = sf.chaflan_superficie(cas, [comun], 2)
    assert g.area(c) == pytest.approx(160 + 20 * math.sqrt(2)) and g.es_valida(c)


# ---------------------------------------------------------------- modificar
def test_recortar_por_plano_superficie_y_aristas():
    cara = cara_cuadrada()
    mitad = sf.recortar(cara, g.Plano("YZ", 5), (8, 5, 0))
    assert g.area(mitad) == pytest.approx(50)
    assert g.caja_envolvente(mitad)[1][0] == pytest.approx(5)
    tool = sf.extruir_superficie(seg((0, 3, -5), (10, 3, -5)), (0, 0, 1), 10)
    r = sf.recortar(cara, tool, (5, 1, 0))
    assert g.area(r) == pytest.approx(70)
    r2 = sf.recortar(cara, [seg((3, 0, 0), (3, 10, 0))], (9, 9, 0))
    assert g.area(r2) == pytest.approx(30) and g.es_valida(r2)
    # Cilindro (cascarón de 3 caras) partido a media altura: dos regiones, cada una con sus caras.
    cas = sf.primitiva_superficie(g.cilindro(5, 10))
    regiones = sf.regiones_recorte(cas, g.Plano("XY", 4))
    assert sorted(round(g.area(x), 6) for x in regiones) == sorted(
        [round(math.pi * 25 + 2 * math.pi * 5 * 4, 6), round(math.pi * 25 + 2 * math.pi * 5 * 6, 6)])
    with pytest.raises(g.ErrorGeometria):
        sf.recortar(cara, g.Plano("YZ", 50), (8, 5, 0))


def test_destrimar():
    disco = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(circulo(5)).Wire(), True)
    disco.Add(TopoDS.Wire(BRepBuilderAPI_MakeWire(circulo(2)).Wire().Reversed()))
    disco = disco.Face()
    assert g.area(disco) == pytest.approx(21 * math.pi)
    assert g.area(sf.destrimar(disco, contornos="interiores")) == pytest.approx(25 * math.pi)
    assert g.area(sf.destrimar(disco, contornos="exteriores")) == pytest.approx(100 - 4 * math.pi)
    todo = sf.destrimar(disco, contornos="todos")
    assert g.area(todo) == pytest.approx(100) and g.es_valida(todo)
    medio_cil = g.caras(sf.revolver_superficie(seg((5, 0, 0), (5, 0, 10)), (0, 0, 0), (0, 0, 1), 120))[0]
    entero = sf.destrimar(medio_cil)
    assert g.area(entero) == pytest.approx(2 * math.pi * 5 * 10)


def test_extender_natural_tangente_perpendicular():
    cara = cara_cuadrada()
    borde = arista_en(cara, (10, 5, 0))
    nat = sf.extender(cara, [borde], 5)
    assert g.area(nat) == pytest.approx(150) and g.caja_envolvente(nat)[1][0] == pytest.approx(15)
    assert len(g.caras(nat)) == 1
    tg = sf.extender(cara, [borde], 5, tipo="tangente")
    assert g.area(tg) == pytest.approx(150) and len(g.caras(tg)) == 2
    pp = sf.extender(cara, [borde], 5, tipo="perpendicular")
    assert g.area(pp) == pytest.approx(150) and g.caja_envolvente(pp)[1][2] == pytest.approx(5)
    medio_cil = g.caras(sf.revolver_superficie(seg((5, 0, 0), (5, 0, 10)), (0, 0, 0), (0, 0, 1), 180))[0]
    arriba = arista_en(medio_cil, (0, 2.5, 10))
    alto = sf.extender(medio_cil, [arriba], 4)
    assert g.area(alto) == pytest.approx(math.pi * 5 * 14) and g.es_valida(alto)
    disco = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(circulo(5)).Wire(), True).Face()
    with pytest.raises(g.ErrorGeometria):
        sf.extender(disco, aristas(disco), 2)


def test_coser_caja_da_solido_y_descoser():
    sueltas = sf.descoser(g.caja(10, 10, 10))
    assert len(sueltas) == 6 and sum(g.area(c) for c in sueltas) == pytest.approx(600)
    r = sf.coser(sueltas)
    assert r["es_solido"] and g.volumen(r["forma"]) == pytest.approx(1000) and g.es_valida(r["forma"])
    abierto = sf.coser(sueltas[:5])
    assert not abierto["es_solido"] and abierto["aristas_libres"] == 4


def test_invertir_normal():
    cara = cara_cuadrada()
    assert g.plano_de_cara(cara).normal[2] == pytest.approx(1)
    inv = sf.invertir_normal(cara)
    assert g.plano_de_cara(inv).normal[2] == pytest.approx(-1)
    with pytest.raises(g.ErrorGeometria):
        sf.invertir_normal(g.caja(1, 1, 1))


def test_engrosar_superficie():
    s = sf.engrosar_superficie(cara_cuadrada(), 2)
    assert g.volumen(s) == pytest.approx(200) and g.es_valida(s)
    assert g.caja_envolvente(s)[1][2] == pytest.approx(2)
    sim = sf.engrosar_superficie(cara_cuadrada(), 2, simetrica=True)
    (_, _, z0), (_, _, z1) = g.caja_envolvente(sim)
    assert (z0, z1) == pytest.approx((-1, 1)) and g.volumen(sim) == pytest.approx(200)
    neg = sf.engrosar_superficie(cara_cuadrada(), -2)
    assert g.caja_envolvente(neg)[0][2] == pytest.approx(-2)
    tubo = sf.engrosar_superficie(lateral(g.cilindro(5, 10)), 1)
    assert g.volumen(tubo) == pytest.approx(math.pi * (36 - 25) * 10) and g.es_valida(tubo)
