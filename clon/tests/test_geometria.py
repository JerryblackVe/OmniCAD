# -*- coding: utf-8 -*-
import math

import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import perfiles as pf
from omnicad.restricciones import Boceto


def test_primitivas_volumen_exacto():
    assert g.volumen(g.caja(10, 20, 30)) == pytest.approx(6000)
    assert g.volumen(g.cilindro(3, 10)) == pytest.approx(math.pi * 9 * 10)
    assert g.volumen(g.esfera(5)) == pytest.approx(4 / 3 * math.pi * 125)
    assert g.volumen(g.toroide(10, 2)) == pytest.approx(2 * math.pi ** 2 * 10 * 4)


def test_booleanos():
    a, b = g.caja(10, 10, 10), g.caja(10, 10, 10, (5, 0, 0))
    assert g.volumen(g.booleano(a, b, "unir")) == pytest.approx(1500)
    assert g.volumen(g.booleano(a, b, "cortar")) == pytest.approx(500)
    assert g.volumen(g.booleano(a, b, "intersecar")) == pytest.approx(500)
    with pytest.raises(g.ErrorGeometria):
        g.booleano(a, b, "xor")


def test_unir_en_L_fusiona_caras_coplanares():
    """Base 80x40x8 + pared 80x8x40 = un prisma en L: 8 caras, no 14 (las coplanares quedaban partidas y un empalme
    exterior mayor que el espesor fallaba)."""
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS

    from omnicad.nucleo import solidos_modificar as sm
    base, pared = g.caja(80, 40, 8), g.caja(80, 8, 40)
    ele = g.booleano(base, pared, "unir")
    assert len(g.caras(ele)) == 8 and g.es_valida(ele)
    assert g.volumen(ele) == pytest.approx(80 * 40 * 8 + 80 * 8 * 32)
    aristas = [TopoDS.Edge(a) for a in g._explorar(ele, TopAbs_EDGE)]
    exterior = min(aristas, key=lambda a: math.dist(g.polilinea_arista(a).mean(axis=0), (40, 0, 0)))
    redondeada = sm.empalme(ele, [{"aristas": [exterior], "radio": 10.0}])
    assert g.es_valida(redondeada) and g.volumen(redondeada) < g.volumen(ele)


def _aristas_libres(forma):
    """Aristas que tocan una sola cara (sin contar las costuras de caras periódicas): las cuenta
    «Revisar geometría» como aristas libres."""
    from OCP.BRep import BRep_Tool
    from OCP.OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    mapa = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, TopAbs_EDGE, TopAbs_FACE, mapa)
    libres = 0
    for i in range(1, mapa.Size() + 1):
        arista = TopoDS.Edge(mapa.FindKey(i))
        if BRep_Tool.Degenerated_s(arista):
            continue
        unicas = []
        for f in mapa.FindFromIndex(i):
            if not any(f.IsSame(u) for u in unicas):
                unicas.append(f)
        if len(unicas) == 1 and not BRep_Tool.IsClosed_s(arista, TopoDS.Face(unicas[0])):
            libres += 1
    return libres


def test_union_tangente_no_deja_aristas_libres():
    """B-28: unir un cuerpo cuyo disco de apoyo queda TANGENTE a la pared interior de un tubo (el puerto
    de oxidante del motor cohete contra la camisa r=45) dejaba cables internos abiertos de una cara:
    el sólido quedaba «no estanco» sin faltarle material."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.TopoDS import TopoDS

    from omnicad.nucleo import solidos_modificar as sm
    # camisa: cilindro r48 (z 55..140) vaciado por arriba y abajo con pared de 3 → tubo abierto r 45..48
    cil = g.cilindro(48, 85, (0, 0, 55))
    tapas = [TopoDS.Face(c) for c in g.caras(cil)
             if BRepAdaptor_Surface(TopoDS.Face(c)).GetType() == GeomAbs_Plane]
    camisa = sm.vaciado(cil, tapas, espesor_interior=3)
    # puerto: tubo r9 (pared 1) con eje +X a la altura z=108, apoyado justo en x=-45 (tangente a r=45)
    puerto = g.trasladar(g.cilindro(9, 26, (0, 0, 108), (1, 0, 0)), (-71, 0, 0))
    puerto = g.booleano(puerto, g.cilindro(7, 46, (-81, 0, 108), (1, 0, 0)), "cortar")   # paso Ø14
    unido = g.booleano(camisa, puerto, "unir")
    assert len(g.solidos(unido)) == 1 and g.es_valida(unido)
    # no se pierde material: tubo + puerto − lo que comparten (el tramo embebido en la pared)
    solape = g.booleano(puerto, camisa, "intersecar")
    assert g.volumen(unido) == pytest.approx(
        g.volumen(camisa) + g.volumen(puerto) - g.volumen(solape), rel=1e-3)
    assert _aristas_libres(unido) == 0


@pytest.mark.parametrize("plano", ["XY", "XZ", "YZ"])
def test_perfiles_anillo_y_disco(plano):
    b = Boceto()
    b.agregar_rectangulo((0, 0), (40, 40))
    b.agregar_circulo((20, 20), 5)
    pl = g.Plano(plano, 10)
    perfiles = pf.detectar(b.geometria(), pl)
    assert sorted(round(p.area, 3) for p in perfiles) == [round(math.pi * 25, 3), round(1600 - math.pi * 25, 3)]
    anillo = max(perfiles, key=lambda p: p.area)
    solido = g.extruir([anillo.cara], pl.normal, 5)
    assert g.volumen(solido) == pytest.approx((1600 - math.pi * 25) * 5)
    assert g.es_valida(solido)


def test_firma_sobrevive_a_cambio_de_medidas():
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (40, 40))
    circ = b.agregar_circulo((20, 20), 5)
    antes = {p.firma for p in pf.detectar(b.geometria(), g.Plano())}
    b.curvas[circ].radio = 12
    b.puntos[b.curvas[lineas[1]].p2].x = 70
    despues = {p.firma for p in pf.detectar(b.geometria(), g.Plano())}
    assert antes == despues


def test_extrusion_simetrica_y_negativa():
    b = Boceto()
    b.agregar_rectangulo((0, 0), (10, 10))
    p = pf.detectar(b.geometria(), g.Plano())[0]
    s = g.extruir([p.cara], (0, 0, 1), 20, simetrica=True)
    (_, _, z0), (_, _, z1) = g.caja_envolvente(s)
    assert z0 == pytest.approx(-10, abs=1e-6) and z1 == pytest.approx(10, abs=1e-6)
    s2 = g.extruir([p.cara], (0, 0, 1), -5)
    (_, _, z0), (_, _, z1) = g.caja_envolvente(s2)
    assert z0 == pytest.approx(-5, abs=1e-6) and z1 == pytest.approx(0, abs=1e-6)


def test_revolucion_de_semicirculo_da_esfera():
    b = Boceto()
    a = b.agregar_arco_3_puntos((0, 0), (10, 10), (20, 0))
    b.agregar_linea(b.curvas[a].inicio, b.curvas[a].fin)
    p = pf.detectar(b.geometria(), g.Plano())[0]
    s = g.revolver([p.cara], (0, 0, 0), (1, 0, 0), 360)
    assert g.volumen(s) == pytest.approx(4 / 3 * math.pi * 1000, rel=1e-6)


def test_caja_envolvente_exacta_aun_despues_de_teselar():
    caja = g.caja(80, 40, 8)
    g.teselar(caja, deflexion=0.5)          # el visor teseló la forma antes de medir
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(caja)
    assert (x1 - x0, y1 - y0, z1 - z0) == pytest.approx((80, 40, 8), abs=1e-6)


def test_teselado_y_aristas():
    v, n = g.teselar(g.caja(1, 2, 3))
    assert v.shape == n.shape and v.shape[0] == 36      # 6 caras × 2 triángulos × 3 vértices
    assert len(g.polilineas_aristas(g.caja(1, 2, 3))) == 12


def test_plano_girado_sobre_su_eje_u():
    p = g.Plano("XY", 5).girado(90)                                      # normal +Z → −Y, por el mismo origen
    assert p.normal == pytest.approx([0, -1, 0]) and p.u == pytest.approx([1, 0, 0]) and p.origen == pytest.approx([0, 0, 5])
    assert p.v == pytest.approx([p.normal[1]*p.u[2]-p.normal[2]*p.u[1], p.normal[2]*p.u[0]-p.normal[0]*p.u[2], p.normal[0]*p.u[1]-p.normal[1]*p.u[0]])
    assert g.Plano("XZ").girado(0).normal == pytest.approx(g.Plano("XZ").normal)
    assert g.Plano("YZ").girado(360).normal == pytest.approx(g.Plano("YZ").normal, abs=1e-12)
