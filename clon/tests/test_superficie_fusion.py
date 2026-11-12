# -*- coding: utf-8 -*-
"""SUPERFICIE igual a Fusion: SUP-10, 11, 14 a 19, 21 a 23 y 26. Cada opción nueva con su número (área o caja) y
`es_valida`, en el núcleo, en el paso, en el diálogo y en la API."""
import math
import os

import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.BRep import BRep_Tool
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCP.TopAbs import TopAbs_EDGE, TopAbs_VERTEX
from OCP.GC import GC_MakeArcOfCircle
from OCP.TopoDS import TopoDS
from OCP.GeomAPI import GeomAPI_PointsToBSpline
from OCP.OCP.collections import Array1_gp_Pnt
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Elips, gp_Pln, gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import superficies as sf
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpPrimitiva
from omnicad.timeline.ops_superficie import OpCoser, OpSupExtruir

Z = (0, 0, 1)


# ---------------------------------------------------------------- ayudas
def seg(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, b))).Edge()


def circulo(r, centro=(0, 0, 0)):
    return BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(*map(float, centro)), gp_Dir(0, 0, 1)), r)).Edge()


def aristas(forma):
    return [TopoDS.Edge(e) for e in g._explorar(forma, TopAbs_EDGE)]


def caja(forma):
    return [tuple(round(c, 4) for c in p) for p in g.caja_envolvente(forma)]


def media_luna(radio=20.0):
    """El diámetro sobre X y el semicírculo de arriba: dos esquinas de 90° entre una recta y un arco."""
    arco = BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(radio, 0, 0), gp_Pnt(0, radio, 0), gp_Pnt(-radio, 0, 0)).Value()).Edge()
    return [seg((-radio, 0, 0), (radio, 0, 0)), arco]


def cuadro(lado=10.0, z=0.0):
    p = [(0, 0, z), (lado, 0, z), (lado, lado, z), (0, lado, z)]
    return [seg(p[i], p[(i + 1) % 4]) for i in range(4)]


def arista_en(forma, punto):
    for e in aristas(forma):
        (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(e)
        if np.allclose([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], punto, atol=1e-6):
            return e
    raise AssertionError(f"no hay arista en {punto}")


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ================================================================ SUP-10 extruir
def test_extruir_dos_lados_simetrica_por_mitad_y_desfase_de_inicio():
    linea = seg((0, 0, 0), (10, 0, 0))
    dos = sf.extruir_superficie(linea, Z, 5, lados="dos_lados", distancia2=3)
    assert g.area(dos) == pytest.approx(80) and caja(dos) == [(0, 0, -3), (10, 0, 5)] and g.es_valida(dos)
    mitad = sf.extruir_superficie(linea, Z, 4, lados="simetrica", medida="mitad")
    assert g.area(mitad) == pytest.approx(80) and caja(mitad)[0][2] == pytest.approx(-4)
    total = sf.extruir_superficie(linea, Z, 8, lados="simetrica", medida="total")
    assert g.area(total) == pytest.approx(80) and caja(total) == [(0, 0, -4), (10, 0, 4)]
    desfasada = sf.extruir_superficie(linea, Z, 5, desfase_inicio=2)
    assert caja(desfasada) == [(0, 0, 2), (10, 0, 7)] and g.es_valida(desfasada)
    cono = sf.extruir_superficie(linea, Z, 5, lados="dos_lados", distancia2=3, conicidad=10)
    assert g.es_valida(cono) and g.area(cono) > 80
    with pytest.raises(g.ErrorGeometria):
        sf.extruir_superficie(linea, Z, 5, lados="dos_lados")          # falta la distancia del lado 2
    with pytest.raises(g.ErrorGeometria):
        sf.extruir_superficie(linea, Z, 5, lados="tres")


def test_extruir_con_distancia_negativa_conserva_la_normal_de_siempre():
    """Una receta vieja con distancia negativa daba la normal hacia -Y (prisma hacia abajo): no se da vuelta."""
    linea = seg((0, 0, 0), (10, 0, 0))
    hacia_abajo = sf.extruir_superficie(linea, Z, -5)
    assert caja(hacia_abajo) == [(0, 0, -5), (10, 0, 0)]
    assert sf.normal_muestra(hacia_abajo)[1] == pytest.approx((0, -1, 0))
    assert sf.normal_muestra(sf.extruir_superficie(linea, Z, 5))[1] == pytest.approx((0, 1, 0))
    objeto = sf.extruir_superficie(linea, Z, 5, hasta=g.Plano("XY", -3.0))
    assert caja(objeto) == [(0, 0, -3), (10, 0, 0)]


def test_extruir_hasta_un_plano_un_cuerpo_y_todo():
    linea = seg((0, 0, 0), (10, 0, 0))
    plano = g.Plano("XY", 7.0)
    a_plano = sf.extruir_superficie(linea, Z, 5, hasta=plano)
    assert g.area(a_plano) == pytest.approx(70) and caja(a_plano)[1][2] == pytest.approx(7) and g.es_valida(a_plano)
    con_desfase = sf.extruir_superficie(linea, Z, 5, hasta=plano, hasta_desfase=2)
    assert g.area(con_desfase) == pytest.approx(90)
    con_lado2 = sf.extruir_superficie(linea, Z, 5, hasta=plano, lados="dos_lados", distancia2=2)
    assert g.area(con_lado2) == pytest.approx(90) and caja(con_lado2)[0][2] == pytest.approx(-2)
    bajo = sf.extruir_superficie(linea, Z, 5, hasta=g.Plano("XY", -3.0))        # el objeto está abajo: va hacia él
    assert caja(bajo) == [(0, 0, -3), (10, 0, 0)]
    cuerpo = g.trasladar(g.caja(30, 30, 4), np.array([-10.0, -15.0, 4.0]))      # tapa abajo en z = 4
    a_cuerpo = sf.extruir_superficie(linea, Z, 5, hasta=cuerpo)
    assert g.area(a_cuerpo) == pytest.approx(40) and g.es_valida(a_cuerpo)
    todo = sf.extruir_superficie(linea, Z, 5, caja=((0, 0, -3), (10, 10, 12)))
    assert caja(todo)[0][2] == pytest.approx(0) and caja(todo)[1][2] > 12 and g.es_valida(todo)
    ambos = sf.extruir_superficie(linea, Z, 5, lados="dos_lados", distancia2=1, caja=((0, 0, -3), (10, 10, 12)))
    assert caja(ambos)[0][2] < -3 and caja(ambos)[1][2] > 12
    with pytest.raises(g.ErrorGeometria):
        sf.extruir_superficie(linea, Z, 5, hasta=plano, lados="simetrica")
    with pytest.raises(g.ErrorGeometria):                                       # el objeto no corta la extrusión
        sf.extruir_superficie(linea, Z, 5, hasta=g.trasladar(g.caja(4, 4, 4), np.array([50.0, 50.0, 50.0])))


# ================================================================ SUP-11 revolución
def test_revolucion_dos_lados_simetrica_y_hasta_un_objeto():
    perfil, origen = seg((10, 0, 0), (10, 0, 10)), (0, 0, 0)
    completa = 2 * math.pi * 10 * 10
    dos = sf.revolver_superficie(perfil, origen, Z, 90, direccion="dos_lados", angulo2=45)
    assert g.area(dos) == pytest.approx(completa * 135 / 360, rel=1e-6) and g.es_valida(dos)
    sim = sf.revolver_superficie(perfil, origen, Z, 90, direccion="simetrica")
    assert g.area(sim) == pytest.approx(completa / 4, rel=1e-6) and caja(sim)[0][0] == pytest.approx(10 * math.cos(math.pi / 4), abs=1e-3)
    a_punto = sf.revolver_superficie(perfil, origen, Z, 0, hasta=("punto", (0, 10, 5)))
    assert g.area(a_punto) == pytest.approx(completa / 4, rel=1e-6)
    a_plano = sf.revolver_superficie(perfil, origen, Z, 0, hasta=("plano", g.Plano("XZ")))
    assert g.area(a_plano) == pytest.approx(completa / 2, rel=1e-6)
    cuerpo = g.trasladar(g.caja(4, 4, 4), np.array([-2.0, 8.0, 3.0]))
    a_cuerpo = sf.revolver_superficie(perfil, origen, Z, 0, hasta=("forma", cuerpo))
    assert 0 < g.area(a_cuerpo) < completa / 2 and g.es_valida(a_cuerpo)
    with pytest.raises(g.ErrorGeometria, match="un solo lado"):
        sf.revolver_superficie(seg((-5, 0, 5), (5, 0, 5)), origen, Z, 90)       # SUP-22: el perfil cruza el eje
    with pytest.raises(g.ErrorGeometria, match="360"):
        sf.revolver_superficie(perfil, origen, Z, 270, direccion="dos_lados", angulo2=180)
    with pytest.raises(g.ErrorGeometria, match="un solo lado"):
        sf.revolver_superficie(perfil, origen, Z, 0, direccion="simetrica", hasta=("punto", (0, 10, 5)))


# ================================================================ SUP-14 parche
def test_parche_continuidad_por_arista_y_guias_interiores():
    tubo = sf.extruir_superficie([circulo(10)], Z, 20)
    borde = arista_en(tubo, (0, 0, 20))
    por_arista = sf.parche([borde], por_arista=[(borde, "G1")], soporte=tubo)
    assert g.area(por_arista) == pytest.approx(math.pi * 100, rel=2e-3) and g.es_valida(por_arista)
    with pytest.raises(g.ErrorGeometria, match="caras vecinas"):                 # SUP-22: dice qué corregir
        sf.parche([borde], por_arista=[(borde, "G1")])
    with pytest.raises(g.ErrorGeometria):
        sf.parche([borde], por_arista=[(borde, "G9")])
    plano = sf.parche([borde])
    domo = sf.parche([borde], interior=[(0, 0, 28)])
    assert g.area(plano) == pytest.approx(math.pi * 100) and g.area(domo) > g.area(plano)
    assert g.caja_envolvente(domo)[1][2] == pytest.approx(28, abs=1e-2)


# ================================================================ SUP-15 reglada
def test_reglada_esquinas_ingleteadas_y_caras_alternas():
    plano = g.Plano("XY")
    simple = sf.reglada(cuadro(), 2, tipo="tangente", referencia=plano)
    ingleteada = sf.reglada(cuadro(), 2, tipo="tangente", referencia=plano, ingletear=True)
    assert g.area(simple) == pytest.approx(80)
    assert g.area(ingleteada) == pytest.approx(14 * 14 - 100) and g.es_valida(ingleteada)      # marco de 2 mm, esquinas vivas
    assert caja(ingleteada) == [(-2, -2, 0), (12, 12, 0)]
    en_direccion = sf.reglada(cuadro(), 3, tipo="direccion", direccion=Z, referencia=plano, ingletear=True)
    assert g.area(en_direccion) == pytest.approx(120) and g.es_valida(en_direccion)
    redonda = sf.reglada([circulo(5)], 2, tipo="tangente", referencia=plano, ingletear=True)
    assert g.area(redonda) == pytest.approx(math.pi * (49 - 25)) and g.es_valida(redonda)       # sin esquinas: el anillo de siempre
    cubo = g.caja(10, 10, 10)
    arista = aristas(cubo)[0]
    una = sf.reglada([arista], 2, referencia=cubo)
    otra = sf.reglada([arista], 2, referencia=cubo, alternas=True)
    assert g.area(una) == pytest.approx(g.area(otra)) and caja(una) != caja(otra) and g.es_valida(otra)


def _esperado_media_luna(radio, d):
    """Área exacta de la media luna con esquinas vivas a distancia `d` (hacia afuera si d > 0): la franja de la recta, la
    corona del arco y, en cada esquina, lo que el inglete suma (d > 0) o recorta (d < 0). Integral numérica en y."""
    corona = math.pi * abs((radio + d) ** 2 - radio ** 2) / 2
    x = math.sqrt((radio + d) ** 2 - d ** 2)                # donde la recta de la franja corta la circunferencia lejana
    ys = np.linspace(0.0, abs(d), 20001)
    linea = radio + (x - radio) * ys / abs(d)               # el borde de la esquina: del vértice al punto de cruce
    if d > 0:
        esquina = np.trapezoid(np.sqrt((radio + d) ** 2 - ys ** 2) - linea, ys)
        franja = (2 * radio + 2 * x) / 2 * d
        return franja + corona + 2 * esquina
    esquina = np.trapezoid(np.sqrt(radio ** 2 - ys ** 2) - linea, ys)
    franja = (2 * radio + 2 * x) / 2 * -d
    return franja + corona - 2 * esquina


def test_reglada_ingleteada_entre_recta_y_arco():
    """SUP-15: las esquinas ingleteadas también entre una recta y un arco (y entre arcos), no solo entre rectas."""
    plano = g.Plano("XY")
    afuera = sf.reglada(media_luna(), 5, tipo="tangente", referencia=plano, ingletear=True)
    sin = sf.reglada(media_luna(), 5, tipo="tangente", referencia=plano)
    assert g.area(sin) == pytest.approx(200 + math.pi * (25 ** 2 - 20 ** 2) / 2) and g.es_valida(sin)
    assert g.area(afuera) == pytest.approx(_esperado_media_luna(20, 5), rel=1e-3) and g.es_valida(afuera)
    assert g.area(afuera) > g.area(sin) + 20
    x = math.sqrt(25 ** 2 - 5 ** 2)                                   # la esquina viva queda en (±24,49; -5)
    assert caja(afuera)[0][:2] == pytest.approx((-25, -5), abs=1e-3)
    esquina = [v for v in g._explorar(afuera, TopAbs_VERTEX)]
    puntos = [np.array([p.X(), p.Y(), p.Z()]) for p in (BRep_Tool.Pnt_s(TopoDS.Vertex(v)) for v in esquina)]
    assert any(np.allclose(p, (x, -5, 0), atol=1e-4) for p in puntos) and any(np.allclose(p, (-x, -5, 0), atol=1e-4) for p in puntos)
    adentro = sf.reglada(media_luna(), -3, tipo="tangente", referencia=plano, ingletear=True)       # se recorta en vez de prolongar
    assert g.area(adentro) == pytest.approx(_esperado_media_luna(20, -3), rel=5e-3) and g.es_valida(adentro)
    assert g.area(adentro) < g.area(sf.reglada(media_luna(), -3, tipo="tangente", referencia=plano))
    with pytest.raises(g.ErrorGeometria, match="recortan una arista"):
        sf.reglada([seg((0, 0, 0), (1, 0, 0)), seg((1, 0, 0), (1, 1, 0)), seg((1, 1, 0), (0, 1, 0)), seg((0, 1, 0), (0, 0, 0))],
                   -5, tipo="tangente", referencia=plano, ingletear=True)


# ================================================================ SUP-16 destrimar
def _placa_con_agujero(radio=3.0):
    mk = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 0, 20, 0, 20)
    mk.Add(TopoDS.Wire(BRepBuilderAPI_MakeWire(circulo(radio, (10, 10, 0))).Wire().Reversed()))   # el agujero va al revés
    return mk.Face()


def test_destrimar_manual_extension_y_los_modos_de_siempre():
    placa = _placa_con_agujero()
    hueco = math.pi * 9
    assert g.area(placa) == pytest.approx(400 - hueco)
    agujero = arista_en(placa, (10, 10, 0))
    tapada = sf.destrimar(placa, contornos="manual", aristas=[agujero])
    assert g.area(tapada) == pytest.approx(400) and g.es_valida(tapada)
    borde = arista_en(placa, (10, 0, 0))
    natural = sf.destrimar(placa, contornos="manual", aristas=[borde])
    assert g.area(natural) == pytest.approx(400 - hueco) and g.es_valida(natural)    # el agujero se conserva
    estirada = sf.destrimar(placa, contornos="exteriores", extension=2)
    assert g.area(estirada) == pytest.approx(24 * 24 - hueco) and caja(estirada) == [(-2, -2, 0), (22, 22, 0)]
    assert g.area(sf.destrimar(placa, contornos="todos")) == pytest.approx(400)
    assert g.area(sf.destrimar(placa, contornos="interiores")) == pytest.approx(400)
    with pytest.raises(g.ErrorGeometria, match="aristas"):
        sf.destrimar(placa, contornos="manual")
    with pytest.raises(g.ErrorGeometria, match="negativa"):
        sf.destrimar(placa, extension=-1)
    with pytest.raises(g.ErrorGeometria, match="ningun|Ningun"):
        sf.destrimar(placa, contornos="manual", aristas=[seg((100, 100, 0), (101, 100, 0))])


# ================================================================ SUP-17 extender
def test_extender_alineacion_libre_en_una_cara_plana_no_rectangular():
    triangulo = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(
        *[seg(a, b) for a, b in [((0, 0, 0), (10, 0, 0)), ((10, 0, 0), (0, 10, 0)), ((0, 10, 0), (0, 0, 0))]]).Wire(), True).Face()
    hipotenusa = arista_en(triangulo, (5, 5, 0))
    libre = sf.extender(triangulo, [hipotenusa], 2, alineacion="libre")
    assert g.area(libre) == pytest.approx(50 + 10 * math.sqrt(2) * 2) and g.es_valida(libre)
    with pytest.raises(g.ErrorGeometria, match="no es rectangular"):
        sf.extender(triangulo, [hipotenusa], 2, alineacion="alinear")
    with pytest.raises(g.ErrorGeometria, match="no es rectangular"):
        sf.extender(triangulo, [hipotenusa], 2)                                      # por defecto: como siempre
    with pytest.raises(g.ErrorGeometria, match="Alineación"):
        sf.extender(triangulo, [hipotenusa], 2, alineacion="g3")
    cuadrada = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 0, 10, 0, 10).Face()
    lado = arista_en(cuadrada, (10, 5, 0))
    for alineacion in ("libre", "alinear"):                                          # rectangular: dan lo mismo
        assert g.area(sf.extender(cuadrada, [lado], 5, alineacion=alineacion)) == pytest.approx(150)


def _casquete_inclinado(radio=10.0, grados=20.0, inclinacion=60.0):
    """La cara esférica de un casquete de `grados` de apertura, con el eje inclinado: su borde es una circunferencia que
    no es iso-paramétrica (la cara no es rectangular en UV)."""
    eje = np.array([0.0, math.sin(math.radians(inclinacion)), math.cos(math.radians(inclinacion))])
    plano = gp_Pln(gp_Pnt(*(eje * radio * math.cos(math.radians(grados)))), gp_Dir(*eje))
    mitad = BRepPrimAPI_MakeHalfSpace(BRepBuilderAPI_MakeFace(plano).Face(), gp_Pnt(*(eje * (radio + 1)))).Solid()
    return next(c for c in g.caras(BRepAlgoAPI_Common(g.esfera(radio), mitad).Shape()) if abs(g.area(c) - 2 * math.pi * radio ** 2
                * (1 - math.cos(math.radians(grados)))) < 1e-6)


def test_extender_alineacion_libre_en_una_cara_curva_no_rectangular():
    """SUP-17: con alineación libre, una cara esférica (borde inclinado) se extiende sobre su propia esfera."""
    radio = 10.0
    cara = _casquete_inclinado(radio)
    borde = aristas(cara)[0]
    for d in (2.0, 4.0):
        libre = sf.extender(cara, [borde], d, alineacion="libre")
        esperado = 2 * math.pi * radio ** 2 * (1 - math.cos(math.radians(20) + d / radio))         # casquete más grande
        assert g.area(libre) == pytest.approx(esperado, rel=2e-3) and g.es_valida(libre) and len(g.caras(libre)) == 2
        assert sf.coser_previa(libre)["aristas_libres"] == 1                                         # cosida: solo el borde nuevo
        franja = [g.caras(libre)[1] if g.area(g.caras(libre)[0]) < g.area(g.caras(libre)[1]) else g.caras(libre)[0]]
        lejos = np.array([c for e in aristas(franja[0]) for c in sf._polilinea(e)])
        assert np.allclose(np.linalg.norm(lejos, axis=1), radio, atol=2e-3)                          # todo sobre la esfera
    domo = sf.parche([circulo(10)], interior=[(0, 0, 6)])                   # B-spline de relleno: se prolonga con ExtendFace
    con_domo = sf.extender(domo, aristas(domo)[:1], 2, alineacion="libre")
    anillo = g.area(con_domo) - g.area(domo)
    assert 2 * math.pi * 10 * 2 < anillo < 2 * math.pi * 10 * 2 * 1.2 and g.es_valida(con_domo)    # más que plano: el domo baja en el borde
    assert sf.coser_previa(con_domo)["aristas_libres"] == 1
    with pytest.raises(g.ErrorGeometria, match="no es rectangular"):
        sf.extender(cara, [borde], 2, alineacion="alinear")
    with pytest.raises(g.ErrorGeometria, match="no es rectangular"):
        sf.extender(cara, [borde], 2)                                                                # el valor por defecto no cambia
    # un cilindro cortado en oblicuo: el borde es una elipse; desarrollado, la franja mide distancia por el largo del borde
    cilindro = g.cilindro(radio, 30)
    inclinado = gp_Pln(gp_Pnt(0, 0, 25), gp_Dir(0.3, 0, 1))
    cortado = BRepAlgoAPI_Common(cilindro, BRepPrimAPI_MakeHalfSpace(BRepBuilderAPI_MakeFace(inclinado).Face(), gp_Pnt(0, 0, 0)).Solid()).Shape()
    pared = next(c for c in g.caras(cortado) if BRep_Tool.Surface_s(c).DynamicType().Name() == "Geom_CylindricalSurface")
    elipse = next(e for e in aristas(pared) if g.caja_envolvente(e)[0][2] > 20)
    larga = sf.extender(pared, [elipse], 3, alineacion="libre")
    theta = np.linspace(0, 2 * math.pi, 20001)
    largo = np.trapezoid(np.sqrt(radio ** 2 + (0.3 * radio * np.sin(theta)) ** 2), theta)      # largo del borde desarrollado
    assert g.area(larga) - g.area(pared) == pytest.approx(3 * largo, rel=2e-3) and g.es_valida(larga)
    puntos = np.array([q for e in aristas(larga) for q in sf._polilinea(e)])
    assert np.abs(np.hypot(puntos[:, 0], puntos[:, 1]) - radio).max() < 1e-4                      # sigue siendo el cilindro


def _spline(puntos):
    arreglo = Array1_gp_Pnt(1, len(puntos))
    for i, p in enumerate(puntos):
        arreglo.SetValue(i + 1, gp_Pnt(*map(float, p)))
    return BRepBuilderAPI_MakeEdge(GeomAPI_PointsToBSpline(arreglo).Curve()).Edge()


@pytest.mark.parametrize("clase", ["revolucion", "extrusion", "offset"])
def test_extender_libre_en_superficies_de_revolucion_extrusion_y_offset(clase):
    """Superficies que no son analíticas ni B-spline: la extensión libre da una cara válida o un error en español, nunca
    el mensaje crudo del kernel."""
    if clase == "revolucion":
        elipse = BRepBuilderAPI_MakeEdge(gp_Elips(gp_Ax2(gp_Pnt(10, 0, 10), gp_Dir(0, 1, 0)), 6, 3), 0.3, 2.5).Edge()
        forma, quitar = sf.revolver_superficie([elipse], (0, 0, 0), Z, 360), (10, 0, 30)
    else:
        forma = sf.extruir_superficie([_spline([(0, 0, 0), (5, 4, 0), (10, -3, 0), (15, 2, 0), (20, 0, 0)])], Z, 12)
        forma, quitar = (sf.desfasar_superficie(forma, 0.4) if clase == "offset" else forma), (10, 0, 20)
    corte = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(10, 0, 6), gp_Dir(0.25, 0.1, 1)), -80, 80, -80, 80).Face()
    cara = g.caras(sf.recortar(g.caras(forma)[0], corte, quitar))[0]
    nombre = BRep_Tool.Surface_s(cara).DynamicType().Name()
    assert nombre in ("Geom_SurfaceOfRevolution", "Geom_SurfaceOfLinearExtrusion", "Geom_OffsetSurface")
    libres = [e for e in aristas(cara) if len(sf._caras_de(sf._mapa_aristas(cara), e)) == 1]
    hechas = 0
    for borde in libres:
        try:
            ext = sf.extender(cara, [borde], 1.0, alineacion="libre")
        except g.ErrorGeometria as e:
            assert "extensión tangente" in str(e) or "aristas libres" in str(e)
            continue
        assert g.es_valida(ext) and g.area(ext) > g.area(cara)
        hechas += 1
    assert hechas >= 1


def test_extender_libre_traduce_cualquier_excepcion_del_kernel(monkeypatch):
    cara = _casquete_inclinado()

    def rota(*_a, **_k):
        raise RuntimeError("Standard_OutOfRange: Geom_BSplineSurface::D1")
    monkeypatch.setattr(sf, "_extension_libre", rota)
    with pytest.raises(g.ErrorGeometria, match="extensión tangente") as e:
        sf.extender(cara, [aristas(cara)[0]], 2, alineacion="libre")
    assert "Standard_OutOfRange" not in str(e.value)


# ================================================================ SUP-18 descoser por caras
def test_descoser_caras_sueltas_y_lo_demas_queda_cosido():
    cubo = g.caja(10, 10, 10)
    cara = g.caras(cubo)[0]
    resto, sueltas = sf.descoser_caras(cubo, [cara])
    assert len(sueltas) == 1 and g.area(sueltas[0]) == pytest.approx(100)
    assert g.area(resto) == pytest.approx(500) and len(g.caras(resto)) == 5 and g.es_valida(resto)
    resto, sueltas = sf.descoser_caras(cubo, g.caras(cubo))
    assert resto is None and len(sueltas) == 6
    with pytest.raises(g.ErrorGeometria, match="no pertenecen"):
        sf.descoser_caras(cubo, [g.caras(g.caja(5, 5, 5))[0]])


# ================================================================ SUP-21 coser
def test_coser_cuenta_los_bordes_libres_y_dice_donde_estan():
    uno = sf.extruir_superficie(cuadro()[0], Z, 5)
    dos = sf.extruir_superficie(cuadro()[1], Z, 5)
    r = sf.coser([uno, dos], 0.01)
    assert not r["es_solido"] and r["aristas_libres"] == 6 and len(r["libres_en"]) == 6
    assert all(len(p) == 3 for p in r["libres_en"])
    previa = sf.coser_previa([uno, dos], 0.01)
    assert previa["aristas_libres"] == 6
    assert sf.coser([uno, dos], 0.01)["aristas_libres"] == 6                          # la vista previa no tocó nada
    cerrada = sf.coser(g.caras(g.caja(10, 10, 10)))
    assert cerrada["es_solido"] and cerrada["libres_en"] == []


# ================================================================ SUP-23 normal
def test_normal_de_una_superficie_apunta_al_lado_positivo():
    cara = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 0, 10, 0, 10).Face()
    punto, normal = sf.normal_muestra(cara)
    assert normal == pytest.approx((0, 0, 1)) and punto[2] == pytest.approx(0)
    _, invertida = sf.normal_muestra(sf.invertir_normal(cara))
    assert invertida == pytest.approx((0, 0, -1))
    desfasada = sf.desfasar_superficie(cara, 3)                                       # positivo = hacia la normal
    assert caja(desfasada)[0][2] == pytest.approx(3)
    p, n = sf.normal_muestra(_placa_con_agujero())                                    # el punto está sobre la cara
    assert not np.allclose(p[:2], (10, 10), atol=2.9)


def _tubo(perfil, **extra):
    doc, b = Documento(), Boceto()
    perfil(b)
    op = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    doc.agregar(op)
    sup = OpSupExtruir(doc.nuevo_id(), curvas=[{"tipo": "curva_boceto", "boceto": op.id, "curva": c} for c in op.boceto.curvas],
                       distancia="30 mm", **extra)
    assert doc.agregar(sup).estado == "ok"
    return doc, sup


def _circulo_20(b):
    b.agregar_circulo(b.agregar_punto(0, 0), 20)


def _cuadrado_20(b):
    a, c, d, e = (b.agregar_punto(*p) for p in ((-10, -10), (10, -10), (10, 10), (-10, 10)))
    for p, q in ((a, c), (c, d), (d, e), (e, a)):
        b.agregar_linea(p, q)


def _radio_x(forma):
    a, b = caja(forma)
    return (b[0] - a[0]) / 2


@pytest.mark.parametrize("perfil, base", [(_circulo_20, 20), (_cuadrado_20, 10)])
def test_sup23_el_desfase_positivo_agranda_el_tubo_como_en_fusion(perfil, base):
    doc, sup = _tubo(perfil)
    forma = doc.estado_final.cuerpos[f"{sup.id}.c1"].forma
    assert _radio_x(sf.desfasar_superficie(forma, 5)) == pytest.approx(base + 5, abs=1e-3)
    assert _radio_x(sf.desfasar_superficie(forma, -5)) == pytest.approx(base - 5, abs=1e-3)
    for cara in g.caras(forma):                               # las paredes del cuadrado, las 4 hacia afuera
        p, n = sf.normal_muestra(cara)
        assert float(p[:2] @ n[:2]) > 0


def test_sup23_el_sentido_no_depende_de_como_se_recorre_el_contorno():
    def al_reves(b):
        a, c, d, e = (b.agregar_punto(*p) for p in ((-10, -10), (-10, 10), (10, 10), (10, -10)))
        for p, q in ((a, c), (c, d), (d, e), (e, a)):
            b.agregar_linea(p, q)
    doc, sup = _tubo(al_reves)
    forma = doc.estado_final.cuerpos[f"{sup.id}.c1"].forma
    assert _radio_x(sf.desfasar_superficie(forma, 5)) == pytest.approx(15, abs=1e-3)


def test_sup23_una_receta_vieja_conserva_su_lado_y_editarla_tambien():
    doc, sup = _tubo(_circulo_20)
    datos = doc.a_dict()
    del datos["operaciones"][-1]["params"]["version_normal"]
    viejo = Documento.desde_dict(datos)
    op = viejo.operaciones[-1]
    assert op.p["version_normal"] == 1
    forma = viejo.estado_final.cuerpos[f"{op.id}.c1"].forma
    assert _radio_x(sf.desfasar_superficie(forma, 5)) == pytest.approx(15, abs=1e-3)          # como siempre: +5 achica


def test_sup23_invertir_normal_muestra_la_flecha_del_lado_que_queda():
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import CATALOGO
    doc, sup = _tubo(_circulo_20)
    cuerpo = f"{sup.id}.c1"
    v = {"cuerpos": [_hit_cuerpo(doc, cuerpo)]}
    flechas = CATALOGO["invertir_normal"]().manipuladores(ContextoComando(doc), v)
    punto, normal = sf.normal_muestra(doc.estado_final.cuerpos[cuerpo].forma)
    assert len(flechas) == 1 and isinstance(flechas[0], mp.FlechaNormal)
    assert flechas[0].origen == pytest.approx(punto) and flechas[0].direccion == pytest.approx(-normal)
    assert CATALOGO["invertir_normal"]().manipuladores(ContextoComando(doc), {"cuerpos": []}) == []


@pytest.mark.parametrize("sentido", [1, -1])
def test_sup23_a_objeto_con_dos_lados_los_dos_tramos_quedan_hacia_afuera(sentido):
    eje = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, sentido))
    alambre = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(gp_Circ(eje, 20.0)).Edge()).Wire()
    tubo = sf.extruir_superficie(alambre, np.array([0.0, 0.0, 1.0]), 5, hasta=g.Plano("XY", 30.0), lados="dos_lados",
                                 distancia2=10, afuera=True)
    for _, tris in g.teselar_por_cara(tubo):
        areas = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        assert np.sum(tris.mean(axis=1)[:, :2] * areas[:, :2]) > 0      # ∑ radial·normal: hacia afuera en cada tramo


def test_sup23_una_curva_abierta_no_cambia_de_lado():
    linea = seg((0, 0, 0), (10, 0, 0))
    assert sf.normal_muestra(sf.extruir_superficie(linea, Z, 5, afuera=True))[1] == pytest.approx((0, 1, 0))


# ================================================================ pasos y diálogos
def _h(doc, ref):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref(ref, doc.estado_final)


def _ejecutar(doc, clase, **valores):
    from omnicad.ui.comando import ContextoComando
    cmd, ctx = clase(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    op = cmd.construir(v, ctx)
    res = doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    return op, res


def _boceto(doc, plano="XY", lineas=(), rect=None, texto=None):
    b = Boceto()
    ids = [b.agregar_linea(a, c) for a, c in lineas]
    if rect:
        ids += b.agregar_rectangulo(*rect)
    if texto:
        ids.append(b.agregar_texto((0, 0), texto[0], 5.0, 0.0, texto[1]))
    op = OpBoceto(doc.nuevo_id(), plano=plano, boceto=b)
    doc.agregar(op)
    return op.id, ids


def _curvas(doc, bid, ids):
    return [_h(doc, {"tipo": "curva_boceto", "boceto": bid, "curva": i}) for i in ids]


def _ultimo(doc):
    return list(doc.estado_final.cuerpos.values())[-1]


def _hit_cuerpo(doc, cid):
    return _h(doc, {"tipo": "cuerpo", "cuerpo": cid})


def _roundtrip(clase, op, doc):
    """Reabrir el paso en su diálogo y aceptar sin tocar nada da los mismos parámetros."""
    from omnicad.ui.comando import ContextoComando
    cmd, ctx = clase(), ContextoComando(doc, op=op)
    nueva = cmd.construir(cmd.desde_op(op, ctx), ctx)
    assert {k: nueva.p[k] for k in op.p} == op.p, clase.__name__


def test_paso_de_extruir_con_opciones_nuevas_y_la_receta_vieja_se_abre_igual():
    from omnicad.ui.comando import ErrorComando
    from omnicad.ui.comandos.superficie import SupExtruir
    doc = Documento()
    bid, ids = _boceto(doc, lineas=[((0, 0), (10, 0))])
    curvas = _curvas(doc, bid, ids)
    op, _ = _ejecutar(doc, SupExtruir, curvas=curvas, distancia="5 mm", lados="dos_lados", distancia2="3 mm")
    assert g.area(_ultimo(doc).forma) == pytest.approx(80)
    _roundtrip(SupExtruir, op, doc)
    _ejecutar(doc, SupExtruir, curvas=curvas, distancia="5 mm", inicio="desfase", desfase_inicio="2 mm")
    assert caja(_ultimo(doc).forma)[0][2] == pytest.approx(2)
    tapa = OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="30", largo="30", alto="4", x="-10", y="-15", z="8")
    doc.agregar(tapa)
    objeto = _hit_cuerpo(doc, f"{tapa.id}.c1")
    _ejecutar(doc, SupExtruir, curvas=curvas, extension="todo")
    assert caja(_ultimo(doc).forma)[1][2] > 12
    op2, _ = _ejecutar(doc, SupExtruir, curvas=curvas, extension="objeto", hasta=[objeto])
    assert caja(_ultimo(doc).forma)[1][2] == pytest.approx(8) and g.area(_ultimo(doc).forma) == pytest.approx(80)
    _roundtrip(SupExtruir, op2, doc)
    with pytest.raises(ErrorComando, match="objeto hasta donde"):
        _ejecutar(doc, SupExtruir, curvas=curvas, extension="objeto")
    viejo = Documento()                         # receta vieja: solo `simetrica`, ninguna clave nueva
    bid, ids = _boceto(viejo, lineas=[((0, 0), (10, 0))])
    viejo.agregar(OpSupExtruir(viejo.nuevo_id(), "Extrusión", curvas=[c["ref"] for c in _curvas(viejo, bid, ids)],
                               distancia="8 mm", simetrica=True))
    assert viejo.resultados[-1].estado == "ok" and caja(_ultimo(viejo).forma) == [(0, 0, -4), (10, 0, 4)]


def test_extruir_un_texto_de_una_linea_y_el_de_contornos_avisa_por_que_no():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.superficie import SupExtruir
    doc = Documento()
    bid, ids = _boceto(doc, texto=("AB", "OmniCAD Trazo SHX"))
    _ejecutar(doc, SupExtruir, curvas=_curvas(doc, bid, ids), distancia="3 mm")
    assert g.area(_ultimo(doc).forma) > 3 * 10 and g.es_valida(_ultimo(doc).forma)    # todos los trazos, no solo el primero
    otro = Documento()
    bid, ids = _boceto(otro, texto=("AB", "Arial"))
    cmd, ctx = SupExtruir(), ContextoComando(otro)
    valores = {c.clave: c.defecto for c in cmd.campos(ctx)}
    res = otro.agregar(cmd.construir({**valores, "curvas": _curvas(otro, bid, ids), "distancia": "10 mm"}, ctx))
    assert res.estado == "error" and "fuente de una línea" in res.mensaje and "Arial" in res.mensaje


def test_paso_de_revolucion_con_dos_lados_proyectar_eje_y_a_objeto():
    from omnicad.ui.comandos.superficie import SupRevolucion
    doc = Documento()
    bid, ids = _boceto(doc, plano="XZ", lineas=[((10, 0), (10, 10))])
    curvas, eje = _curvas(doc, bid, ids), [_h(doc, {"tipo": "eje", "id": "Z"})]
    completa = 2 * math.pi * 10 * 10
    op, _ = _ejecutar(doc, SupRevolucion, curvas=curvas, eje=eje, lados="dos_lados", angulo="90 deg", angulo2="45 deg")
    assert g.area(_ultimo(doc).forma) == pytest.approx(completa * 135 / 360, rel=1e-6)
    _roundtrip(SupRevolucion, op, doc)
    _ejecutar(doc, SupRevolucion, curvas=curvas, eje=eje, extension="completa")
    assert g.area(_ultimo(doc).forma) == pytest.approx(completa, rel=1e-6)
    _ejecutar(doc, SupRevolucion, curvas=curvas, eje=eje, angulo="90 deg", lados="simetrica", proyectar_eje=True)
    assert g.area(_ultimo(doc).forma) == pytest.approx(completa / 4, rel=1e-6)
    op3, _ = _ejecutar(doc, SupRevolucion, curvas=curvas, eje=eje, extension="objeto",
                       hasta=[_h(doc, {"tipo": "plano", "id": "YZ"})])
    assert g.area(_ultimo(doc).forma) == pytest.approx(completa / 4, rel=1e-6)
    _roundtrip(SupRevolucion, op3, doc)


def test_paso_de_parche_con_continuidad_por_arista_guias_e_invertir():
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.superficie import Parche
    doc = Documento()
    bid, ids = _boceto(doc, rect=((0, 0), (10, 10)))
    contorno = _curvas(doc, bid, ids)
    op, _ = _ejecutar(doc, Parche, contorno=contorno, agrupar=False, continuidades="G0, -, G0")
    assert op.p["continuidades"] == ["G0", "", "G0", ""] and g.area(_ultimo(doc).forma) == pytest.approx(100)
    _roundtrip(Parche, op, doc)
    with pytest.raises(ErrorComando, match="G0, G1 o G2"):
        _ejecutar(doc, Parche, contorno=contorno, agrupar=False, continuidades="G7")
    with pytest.raises(ErrorComando, match="solo 4 aristas"):
        _ejecutar(doc, Parche, contorno=contorno, agrupar=False, continuidades="G0,G0,G0,G0,G0")
    sin = sf.normal_muestra(_ultimo(doc).forma)[1]
    _ejecutar(doc, Parche, contorno=contorno, invertir=True)
    assert sf.normal_muestra(_ultimo(doc).forma)[1] == pytest.approx(-sin)
    cmd, ctx = Parche(), ContextoComando(doc)
    valores = {c.clave: c.defecto for c in cmd.campos(ctx)}
    res = doc.agregar(cmd.construir({**valores, "contorno": contorno, "continuidad": "G1"}, ctx))
    assert res.estado == "error" and "caras vecinas" in res.mensaje and "`soporte`" not in res.mensaje


def test_reglada_ingleteada_avisa_de_la_esquina_que_no_pudo_cortar():
    """Dos aristas 3D con la dirección girada: sus bordes lejanos no se cruzan, la esquina queda abierta y se dice."""
    quiebre = [seg((0, 0, 0), (10, 0, 0)), seg((10, 0, 0), (10, 10, 5))]
    avisos = []
    forma = sf.reglada(quiebre, 3, 30, tipo="direccion", direccion=Z, ingletear=True, avisos=avisos)
    assert g.es_valida(forma) and g.area(forma) == pytest.approx(60) and len(avisos) == 1
    assert "sin cortar" in avisos[0] and "[10.0, 0.0, 0.0]" in avisos[0]
    sin = []
    sf.reglada(quiebre, 3, 0, tipo="direccion", direccion=Z, ingletear=True, avisos=sin)       # misma dirección: coinciden
    sf.reglada(cuadro(), 2, tipo="tangente", referencia=g.Plano("XY"), ingletear=True, avisos=sin)
    assert sin == []
    sf.reglada(quiebre, 3, 30, tipo="direccion", direccion=Z, ingletear=True)                    # sin lista: no falla


def test_paso_de_reglada_ingleteada():
    from omnicad.ui.comandos.superficie import Reglada
    doc = Documento()
    bid, ids = _boceto(doc, rect=((0, 0), (10, 10)))
    op, res = _ejecutar(doc, Reglada, aristas=_curvas(doc, bid, ids), tipo="tangente", distancia="2 mm", ingletear=True)
    assert g.area(_ultimo(doc).forma) == pytest.approx(14 * 14 - 100) and g.es_valida(_ultimo(doc).forma)
    assert res.estado == "ok"                                      # las esquinas cortaron: ningún aviso
    _roundtrip(Reglada, op, doc)
    t = Documento()                                                # tres aristas se juntan en un punto: esa esquina no se corta
    bid, ids = _boceto(t, lineas=[((0, 0), (10, 0)), ((10, 0), (10, 10)), ((10, 0), (10, -10))])
    _, res = _ejecutar(t, Reglada, aristas=_curvas(t, bid, ids), tipo="tangente", distancia="2 mm", ingletear=True)
    assert res.estado == "aviso" and "sin cortar" in res.mensaje and g.es_valida(_ultimo(t).forma)
    vieja = Documento()                          # sin ingletear: una cara por arista, como siempre
    bid, ids = _boceto(vieja, rect=((0, 0), (10, 10)))
    _ejecutar(vieja, Reglada, aristas=_curvas(vieja, bid, ids), tipo="tangente", distancia="2 mm")
    assert g.area(_ultimo(vieja).forma) == pytest.approx(80)


def _recortada(doc):
    """Un parche cuadrado de 10 recortado por un plano en x = 5 (queda la mitad) y el hit de su borde de corte."""
    from omnicad.ui.comandos.superficie import Parche, Recortar
    bid, ids = _boceto(doc, rect=((0, 0), (10, 10)))
    _ejecutar(doc, Parche, contorno=_curvas(doc, bid, ids))
    cuerpo = _ultimo(doc)
    doc.agregar(__import__("omnicad.timeline.operaciones", fromlist=["OpPlano"]).OpPlano(
        doc.nuevo_id(), "Plano1", base="YZ", distancia="5 mm"))
    region = _h(doc, refs.referencia(cuerpo.id, refs.subformas(cuerpo.forma, "cara")[0], cuerpo.forma))
    region["punto"] = np.array([8.0, 5.0, 0.0])
    _ejecutar(doc, Recortar, herramienta=[_h(doc, {"tipo": "plano", "id": "op3"})], region=[region])
    forma = doc.estado_final.cuerpos[cuerpo.id].forma
    assert g.area(forma) == pytest.approx(50)
    corte = next(e for e in refs.subformas(forma, "arista")
                 if abs(g.caja_envolvente(e)[0][0] - 5) < 1e-6 and abs(g.caja_envolvente(e)[1][0] - 5) < 1e-6)
    return cuerpo.id, forma, refs.subformas(forma, "cara")[0], corte


def test_paso_de_destrimar_manual_con_extension_y_copia():
    from omnicad.ui.comando import ErrorComando
    from omnicad.ui.comandos.superficie import Destrimar
    doc = Documento()
    cid, forma, cara, corte = _recortada(doc)
    hit_cara = _h(doc, refs.referencia(cid, cara, forma))
    hit_corte = _h(doc, refs.referencia(cid, corte, forma))
    n0 = len(doc.estado_final.cuerpos)
    op, _ = _ejecutar(doc, Destrimar, caras=[hit_cara], contornos="manual", aristas=[hit_corte])
    assert g.area(doc.estado_final.cuerpos[cid].forma) == pytest.approx(100) and len(doc.estado_final.cuerpos) == n0
    _roundtrip(Destrimar, op, doc)
    doc2 = Documento()
    cid, forma, cara, corte = _recortada(doc2)
    op2, _ = _ejecutar(doc2, Destrimar, caras=[_h(doc2, refs.referencia(cid, cara, forma))], contornos="manual",
                       aristas=[_h(doc2, refs.referencia(cid, corte, forma))], mantener_copia=True, extension="2 mm")
    assert len(doc2.estado_final.cuerpos) == 2
    assert g.area(doc2.estado_final.cuerpos[cid].forma) == pytest.approx(14 * 14) and g.es_valida(doc2.estado_final.cuerpos[cid].forma)
    copia = [c for k, c in doc2.estado_final.cuerpos.items() if k != cid][0]
    assert copia.tipo == "superficie" and g.area(copia.forma) == pytest.approx(50)    # la copia es la superficie recortada
    _roundtrip(Destrimar, op2, doc2)
    with pytest.raises(ErrorComando, match="manual"):
        _ejecutar(doc2, Destrimar, caras=[_h(doc2, refs.referencia(cid, cara, forma))], contornos="manual")


def test_paso_de_coser_avisa_cuantos_bordes_quedan_libres_y_el_diálogo_lo_adelanta():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.superficie import Coser, Descoser, Extender, SupExtruir
    doc = Documento()
    bid, ids = _boceto(doc, lineas=[((0, 0), (10, 0)), ((10, 0), (10, 10))])
    for i in ids:
        _ejecutar(doc, SupExtruir, curvas=_curvas(doc, bid, [i]), distancia="5 mm")
    cuerpos = [_hit_cuerpo(doc, c) for c in doc.estado_final.cuerpos]
    cmd, ctx = Coser(), ContextoComando(doc)                    # el diálogo se abre antes de aplicar la costura
    _, res = _ejecutar(doc, Coser, cuerpos=cuerpos, tolerancia="0.01 mm")
    assert res.estado == "aviso" and "6 bordes libres" in res.mensaje and "cerca de" in res.mensaje
    assert cmd._libres({"cuerpos": cuerpos, "tolerancia": "0.01 mm"}, ctx).startswith("6 bordes libres")
    assert cmd._libres({"cuerpos": [], "tolerancia": "0.01 mm"}, ctx) == "Elegí las superficies."
    assert cmd._libres({"cuerpos": cuerpos, "tolerancia": "abc"}, ctx) == ""
    cerrado = Documento()
    cerrado.agregar(OpPrimitiva(cerrado.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    _ejecutar(cerrado, Descoser, cuerpos=[_hit_cuerpo(cerrado, "op1.c1")])
    todos = [_hit_cuerpo(cerrado, c) for c in cerrado.estado_final.cuerpos]
    assert "Ninguno" in cmd._libres({"cuerpos": todos, "tolerancia": "0.01 mm"}, ContextoComando(cerrado))
    assert "alineacion" in [c.clave for c in Extender().campos(ctx)]
    assert OpCoser.PARAMS["tolerancia"] == "0.01 mm"


def test_paso_de_extender_con_alineacion_libre():
    from omnicad.ui.comandos.superficie import Extender, Parche
    doc = Documento()
    bid, ids = _boceto(doc, lineas=[((0, 0), (10, 0)), ((10, 0), (0, 10)), ((0, 10), (0, 0))])
    _ejecutar(doc, Parche, contorno=_curvas(doc, bid, ids))
    cuerpo = _ultimo(doc)
    hipotenusa = next(e for e in refs.subformas(cuerpo.forma, "arista")
                      if abs(g.caja_envolvente(e)[0][0]) < 1e-6 and abs(g.caja_envolvente(e)[1][0] - 10) < 1e-6
                      and abs(g.caja_envolvente(e)[1][1] - 10) < 1e-6 and abs(g.caja_envolvente(e)[0][1]) < 1e-6)
    hit = _h(doc, refs.referencia(cuerpo.id, hipotenusa, cuerpo.forma))
    from omnicad.ui.comando import ContextoComando
    cmd, ctx = Extender(), ContextoComando(doc)
    valores = {c.clave: c.defecto for c in cmd.campos(ctx)}
    estricto = doc.agregar(cmd.construir({**valores, "aristas": [hit], "distancia": "2 mm"}, ctx))
    assert estricto.estado == "error" and "no es rectangular" in estricto.mensaje
    op, _ = _ejecutar(doc, Extender, aristas=[hit], distancia="2 mm", alineacion="libre")
    assert g.area(doc.estado_final.cuerpos[cuerpo.id].forma) == pytest.approx(50 + 10 * math.sqrt(2) * 2)
    _roundtrip(Extender, op, doc)


def test_paso_de_descoser_solo_las_caras_elegidas():
    from omnicad.ui.comando import ErrorComando
    from omnicad.ui.comandos.superficie import Descoser
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    cuerpo = doc.estado_final.cuerpos["op1.c1"]
    cara = refs.subformas(cuerpo.forma, "cara")[0]
    hit = _h(doc, refs.referencia("op1.c1", cara, cuerpo.forma))
    op, _ = _ejecutar(doc, Descoser, caras=[hit])
    cuerpos = list(doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 2 and all(c.tipo == "superficie" for c in cuerpos)
    assert sorted(round(g.area(c.forma)) for c in cuerpos) == [100, 500]
    _roundtrip(Descoser, op, doc)
    with pytest.raises(ErrorComando):
        _ejecutar(doc, Descoser)


# ================================================================ API (MCP y CLI)
def llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def falla(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert not respuesta["ok"], respuesta
    return respuesta


def _linea(sesion, nombre="Perfil", plano="XY", inicio=(0, 0), fin=(10, 0)):
    llamar(sesion, "create_sketch", name=nombre, plane=plano)
    llamar(sesion, "draw_line", sketch=nombre, start_x=inicio[0], start_y=inicio[1], end_x=fin[0], end_y=fin[1])
    curvas = sesion.doc.estado_final.bocetos[sesion.paso(nombre).id].boceto.curvas
    return {"sketch": nombre, "curve": next(iter(curvas))}


def _forma(sesion, resultado):
    return sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma


def test_api_extruir_con_opciones_de_fusion():
    s = api.Sesion()
    perfil = _linea(s)
    assert g.area(_forma(s, llamar(s, "create_surface_extrude", profiles=perfil, distance=5, sides="two_sides",
                                   distance2=3))) == pytest.approx(80)
    assert g.area(_forma(s, llamar(s, "create_surface_extrude", profiles=perfil, distance=4, sides="symmetric",
                                   symmetric_measure="half"))) == pytest.approx(80)
    assert caja(_forma(s, llamar(s, "create_surface_extrude", profiles=perfil, distance=5, start="offset",
                                 start_offset=2)))[0][2] == pytest.approx(2)
    assert caja(_forma(s, llamar(s, "create_surface_extrude", profiles=perfil, distance=5, flip=True)))[1][2] == pytest.approx(0)
    assert g.area(_forma(s, llamar(s, "create_surface_extrude", profiles=perfil, extent="all"))) > 0
    for malo in ({"start": "object"}, {"extent": "to_object"}):
        assert falla(s, "create_surface_extrude", profiles=perfil, **malo)["error_kind"] == "INVALID_ARGUMENTS"
    tapa = OpPrimitiva(s.doc.nuevo_id(), forma="caja", ancho="30", largo="30", alto="4", x="-10", y="-15", z="8")
    s.doc.agregar(tapa)
    objeto = f"{tapa.id}.c1"
    a_objeto = llamar(s, "create_surface_extrude", profiles=perfil, extent="to_object", to=objeto)
    assert g.area(_forma(s, a_objeto)) == pytest.approx(80)


def test_api_revolucion_parche_reglada_extender_destrimar_y_descoser():
    s = api.Sesion()
    perfil = _linea(s, "Giro", plano="XZ", inicio=(10, 0), fin=(10, 10))
    dos = llamar(s, "create_surface_revolve", profiles=perfil, axis="Z", angle=90, direction="two_sides", angle2=45)
    assert g.area(_forma(s, dos)) == pytest.approx(2 * math.pi * 100 * 135 / 360, rel=1e-6)
    a_plano = llamar(s, "create_surface_revolve", profiles=perfil, axis="Z", to_object="YZ")
    assert g.area(_forma(s, a_plano)) == pytest.approx(2 * math.pi * 100 / 4, rel=1e-6)
    assert falla(s, "create_surface_revolve", profiles=perfil, axis="Z", to_object="YZ",
                 direction="symmetric")["error_kind"] == "INVALID_ARGUMENTS"
    llamar(s, "create_sketch", name="Contorno", plane="XY")
    llamar(s, "draw_rectangle", sketch="Contorno", x1=0, y1=0, x2=10, y2=10)
    contorno = {"sketch": "Contorno", "profile": 0}
    assert g.area(_forma(s, llamar(s, "create_patch", boundary=contorno, flip=True))) == pytest.approx(100)
    assert falla(s, "create_patch", boundary=contorno, group_edges=False)["error_kind"] == "INVALID_ARGUMENTS"
    reglada = llamar(s, "create_ruled_surface", edges=contorno, surface_type="tangent", distance=2, mitered_corners=True)
    assert g.area(_forma(s, reglada)) == pytest.approx(14 * 14 - 100)
    assert falla(s, "unstitch_surfaces")["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "untrim_surface", faces="x", boundaries="manual")["error_kind"] in ("INVALID_ARGUMENTS", "SELECTOR_ERROR", "INVALID_SELECTOR")


def test_api_reglada_ingleteada_con_un_arco_y_extender_libre_en_una_cara_curva():
    """SUP-15 y SUP-17 por la API: una media luna ingleteada y el casquete de un tubo extendido con bordes libres."""
    s = api.Sesion()
    llamar(s, "create_sketch", name="Luna", plane="XY")
    llamar(s, "draw_line", sketch="Luna", start_x=-20, start_y=0, end_x=20, end_y=0)
    llamar(s, "draw_arc", sketch="Luna", start_x=20, start_y=0, mid_x=0, mid_y=20, end_x=-20, end_y=0)
    luna = {"sketch": "Luna", "profile": 0}
    esperados = (_esperado_media_luna(20, 5), _esperado_media_luna(20, -5))               # hacia afuera o hacia adentro
    mitrada = g.area(_forma(s, llamar(s, "create_ruled_surface", edges=luna, surface_type="tangent", distance=5,
                                      mitered_corners=True)))
    sin = g.area(_forma(s, llamar(s, "create_ruled_surface", edges=luna, surface_type="tangent", distance=5)))
    assert min(abs(mitrada - e) / e for e in esperados) < 5e-3 and mitrada != pytest.approx(sin)
    llamar(s, "create_sketch", name="Boca", plane="XY")
    llamar(s, "draw_circle", sketch="Boca", radius=10)
    tubo = llamar(s, "create_surface_extrude", profiles={"sketch": "Boca", "profile": 0}, distance=20)["bodies_created"][0]["id"]
    tapa = llamar(s, "create_patch", boundary={"body": tubo, "edges": ">Z"}, continuity="G1")["bodies_created"][0]["id"]
    antes = g.area(s.cuerpo(tapa).forma)
    assert falla(s, "extend_surface", edges={"body": tapa, "edges": ">Z"}, body=tapa, distance=2)["error_kind"] == "OPERATION_FAILED"
    llamar(s, "extend_surface", edges={"body": tapa, "edges": ">Z"}, body=tapa, distance=2, edge_alignment="free")
    despues = s.cuerpo(tapa).forma
    assert g.area(despues) > antes + 2 * math.pi * 10 * 2 * 0.95 and g.es_valida(despues)


def test_api_escalar_una_superficie_y_la_normal_en_la_escena():
    s = api.Sesion()
    perfil = _linea(s)
    cid = llamar(s, "create_surface_extrude", profiles=perfil, distance=5)["bodies_created"][0]["id"]
    info = next(b for b in llamar(s, "get_scene_info")["bodies"] if b["id"] == cid)
    assert info["type"] == "surface" and len(info["normal"]["point"]) == 3
    assert abs(abs(info["normal"]["direction"][1]) - 1) < 1e-6              # la superficie está en el plano XZ
    antes = g.area(s.cuerpo(cid).forma)
    llamar(s, "scale_body", bodies=[cid], factor=2)
    assert g.area(s.cuerpo(cid).forma) == pytest.approx(antes * 4) and g.es_valida(s.cuerpo(cid).forma)


# ================================================================ SUP-26 y asas
def test_el_asa_de_extender_frena_en_cero_y_la_de_extruir_sigue_los_lados():
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import CATALOGO
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="60", alto="20"))
    cuerpo = doc.estado_final.cuerpos["op1.c1"]
    arista = next(e for e in refs.subformas(cuerpo.forma, "arista") if abs(g.caja_envolvente(e)[1][2] - 20) < 1e-6
                  and abs(g.caja_envolvente(e)[0][2] - 20) < 1e-6)
    hit = _h(doc, refs.referencia("op1.c1", arista, cuerpo.forma))
    extender = CATALOGO["extender_sup"]()
    asas = extender.manipuladores(ContextoComando(doc), {"aristas": [hit]})
    assert [type(a).__name__ for a in asas] == ["Flecha"] and asas[0].minimo == 0.0
    doc2 = Documento()
    bid, ids = _boceto(doc2, lineas=[((0, 0), (10, 0))])
    base = {"curvas": _curvas(doc2, bid, ids), "distancia": "5 mm", "distancia2": "3 mm", "conicidad": "0 deg"}
    cmd, ctx = CATALOGO["sup_extruir"](), ContextoComando(doc2)

    def flechas(**v):
        return [a.clave for a in cmd.manipuladores(ctx, {**base, **v}) if isinstance(a, mp.Flecha)]

    assert flechas(lados="un_lado") == ["distancia"]
    assert flechas(lados="dos_lados") == ["distancia", "distancia2"]
    assert flechas(extension="objeto") == [] and flechas(extension="todo") == []
    assert CATALOGO["sup_revolucion"]().manipuladores(ctx, {"curvas": [], "eje": []}) == []
