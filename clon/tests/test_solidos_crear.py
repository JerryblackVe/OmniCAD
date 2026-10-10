# -*- coding: utf-8 -*-
"""Pruebas numéricas de nucleo/solidos_crear.py (comandos SÓLIDO › CREAR de Fusion)."""
import math
import time

import numpy as np
import pytest
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_MakeWire)
from OCP.GC import GC_MakeArcOfCircle
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pln, gp_Pnt

from omnicad.nucleo import geometria as g
from omnicad.nucleo import perfiles as pf
from omnicad.nucleo import referencias as rf
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import solidos_modificar as sm
from omnicad.restricciones import Boceto

Z = (0, 0, 1)


# ---------------------------------------------------------------- ayudas
def poligono(puntos):
    mk = BRepBuilderAPI_MakePolygon()
    for p in puntos:
        mk.Add(gp_Pnt(*map(float, p)))
    mk.Close()
    return BRepBuilderAPI_MakeFace(mk.Wire(), True).Face()


def rect(x0, y0, x1, y1, z=0.0):
    return poligono([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)])


def alambre_circulo(centro, radio, normal=Z):
    arista = BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(*map(float, centro)), gp_Dir(*map(float, normal))),
                                             radio)).Edge()
    return BRepBuilderAPI_MakeWire(arista).Wire()


def circulo(centro, radio, normal=Z):
    return BRepBuilderAPI_MakeFace(alambre_circulo(centro, radio, normal), True).Face()


def linea(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, b))).Edge()


def arco_xy(radio):
    """Cuarto de círculo de radio dado en el plano XY, de (r, 0, 0) a (0, r, 0)."""
    m = radio * math.sqrt(0.5)
    return BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(radio, 0, 0), gp_Pnt(m, m, 0),
                                                      gp_Pnt(0, radio, 0)).Value()).Edge()


def anillo(z, r_ext, r_int):
    return g.caras(g.booleano(circulo((0, 0, z), r_ext), circulo((0, 0, z), r_int), "cortar"))[0]


def cara_superior(cuerpo, z):
    return [c for c in g.caras(cuerpo) if g.plano_de_cara(c) is not None
            and abs(g.centro_masa(c, superficie=True)[2] - z) < 1e-6 and g.plano_de_cara(c).normal[2] > 0][0]


def caja_de(forma):
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(forma)
    return [x0, y0, z0, x1, y1, z1]


def valido(forma, volumen=None, rel=1e-6):
    assert g.es_valida(forma)
    if volumen is not None:
        assert g.volumen(forma) == pytest.approx(volumen, rel=rel)
    return forma


def canal_u():
    """Piso 40x20x2 y dos paredes de 2 mm de espesor y 12 de alto en x=0 y x=38."""
    return g.unir_todos([g.caja(40, 20, 2), g.caja(2, 20, 12), g.caja(2, 20, 12, (38, 0, 0))])


# ---------------------------------------------------------------- 1. extrusión
def test_extrusion_distancias_y_direcciones_con_perfil_de_boceto():
    b = Boceto()
    b.agregar_rectangulo((0, 0), (10, 10))
    cara = pf.detectar(b.geometria(), g.Plano("XY"))[0].cara
    valido(sc.extruir_avanzado([cara], Z, distancia1=5), 500)
    assert caja_de(sc.extruir_avanzado([cara], Z, distancia1=-5))[2] == pytest.approx(-5)
    s = valido(sc.extruir_avanzado([cara], Z, distancia1=5, inicio_desfase=2), 500)
    assert caja_de(s)[2:6:3] == pytest.approx([2, 7])
    s = valido(sc.extruir_avanzado([cara], Z, direccion="dos_lados", distancia1=5, distancia2=3), 800)
    assert caja_de(s)[2:6:3] == pytest.approx([-3, 5])
    valido(sc.extruir_avanzado([cara], Z, direccion="simetrica", distancia1=5), 1000)
    valido(sc.extruir_avanzado([cara], Z, direccion="simetrica", distancia1=5, medida_simetrica="total"), 500)
    with pytest.raises(g.ErrorGeometria):
        sc.extruir_avanzado([cara], Z)


def test_extrusion_con_inclinacion_tronco_de_piramide_y_cono():
    q = rect(0, 0, 10, 10)
    t = math.tan(math.radians(5))
    ancho, angosto = 10 + 20 * t, 10 - 20 * t
    tronco = lambda a: 10 / 3 * (100 + a * a + 10 * a)  # noqa: E731
    s = valido(sc.extruir_avanzado([q], Z, distancia1=10, conicidad1=5), tronco(ancho))
    assert caja_de(s)[3] == pytest.approx(10 + 10 * t)          # esquinas vivas: se ensancha 10·tan
    valido(sc.extruir_avanzado([q], Z, distancia1=10, conicidad1=-5), tronco(angosto))
    valido(sc.extruir_avanzado([q], Z, distancia1=-10, conicidad1=5), tronco(ancho))
    r2 = 5 + 10 * t
    valido(sc.extruir_avanzado([circulo((0, 0, 0), 5)], Z, distancia1=10, conicidad1=5),
           math.pi * 10 / 3 * (25 + r2 * r2 + 5 * r2))
    # dos lados con conicidades distintas: suma de los dos troncos
    s = sc.extruir_avanzado([q], Z, direccion="dos_lados", distancia1=10, distancia2=10, conicidad1=5,
                            conicidad2=-5)
    valido(s, tronco(ancho) + tronco(angosto))


def test_extrusion_delgada_perfiles_cerrados_y_abiertos():
    q = rect(0, 0, 10, 10)
    valido(sc.extruir_avanzado([q], Z, distancia1=5, delgado={"espesor": 1, "ubicacion": "lado1"}), (144 - 100) * 5)
    valido(sc.extruir_avanzado([q], Z, distancia1=5, delgado={"espesor": 1, "ubicacion": "lado2"}), (100 - 64) * 5)
    valido(sc.extruir_avanzado([q], Z, distancia1=5, delgado={"espesor": 1, "ubicacion": "centro"}), (121 - 81) * 5)
    # anillo: una pared por cada lazo, hacia afuera de cada uno
    s = sc.extruir_avanzado([anillo(0, 5, 2)], Z, distancia1=4, delgado={"espesor": 1, "ubicacion": "lado1"})
    valido(s, math.pi * ((36 - 25) + (9 - 4)) * 4)
    # perfil abierto en L, pared centrada; y una línea con la pared a la izquierda (y > 0)
    s = sc.extruir_avanzado([], Z, distancia1=5, aristas=[linea((0, 0, 0), (10, 0, 0)), linea((10, 0, 0), (10, 10, 0))],
                            delgado={"espesor": 1, "ubicacion": "centro"})
    valido(s, 20 * 5)
    s = valido(sc.extruir_avanzado([], Z, distancia1=5, aristas=[linea((0, 0, 0), (10, 0, 0))],
                                   delgado={"espesor": 1, "ubicacion": "lado1"}), 50)
    assert caja_de(s)[1:5:3] == pytest.approx([0, 1])
    with pytest.raises(g.ErrorGeometria):
        sc.extruir_avanzado([], Z, distancia1=5, aristas=[linea((0, 0, 0), (10, 0, 0))])


def test_extrusion_hasta_objeto_y_todo():
    q = rect(0, 0, 10, 10)
    valido(sc.extruir_avanzado([q], Z, hasta=rect(-50, -50, 50, 50, 7)), 700)
    valido(sc.extruir_avanzado([q], Z, hasta=rect(-50, -50, 50, 50, 7), hasta_desfase=1), 800)
    oblicuo = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, 10), gp_Dir(1, 0, 1)), -30, 30, -30, 30).Face()
    valido(sc.extruir_avanzado([q], Z, hasta=oblicuo), 500)            # techo z = 10 − x
    esfera = g.esfera(20, (5, 5, 40))
    hasta_cuerpo = valido(sc.extruir_avanzado([q], Z, hasta=esfera, hasta_modo="cuerpo"))
    a_traves = valido(sc.extruir_avanzado([q], Z, hasta=esfera, hasta_modo="a_traves"))
    assert caja_de(hasta_cuerpo)[5] == pytest.approx(40 - math.sqrt(400 - 50))   # esquina más alta bajo la esfera
    assert caja_de(a_traves)[5] == pytest.approx(60)                               # sale por arriba de la esfera
    assert g.volumen(g.booleano(hasta_cuerpo, esfera, "intersecar")) == pytest.approx(0, abs=1e-6)
    # hasta la cara curva de la esfera = hasta el cuerpo (la parte de abajo)
    curva = valido(sc.extruir_avanzado([q], Z, hasta=g.caras(esfera)[0]))
    assert g.volumen(curva) == pytest.approx(g.volumen(hasta_cuerpo), rel=1e-6)
    valido(sc.extruir_avanzado([q], Z, hasta_caja=((-5, -5, -3), (20, 20, 12))), 100 * 13)
    valido(sc.extruir_avanzado([q], Z, direccion="simetrica", hasta_caja=((-5, -5, -3), (20, 20, 12))), 100 * 17)


# ---------------------------------------------------------------- 2. revolución
def test_revolucion_un_lado_simetrica_dos_lados_y_delgada():
    perfil = poligono([(5, 0, 0), (7, 0, 0), (7, 0, 4), (5, 0, 4)])
    eje = ((0, 0, 0), Z)
    completo = 8 * 2 * math.pi * 6                                     # Pappus: área · 2π · radio del centroide
    valido(sc.revolver_avanzado([perfil], *eje), completo)
    valido(sc.revolver_avanzado([perfil], *eje, angulo1=90), completo / 4)
    s = valido(sc.revolver_avanzado([perfil], *eje, direccion="simetrica", angulo1=45), completo / 4)
    assert caja_de(s)[1] == pytest.approx(-caja_de(s)[4])             # simétrica respecto del plano del perfil
    valido(sc.revolver_avanzado([perfil], *eje, direccion="dos_lados", angulo1=30, angulo2=60), completo / 4)
    valido(sc.revolver_avanzado([], *eje, aristas=[linea((5, 0, 0), (5, 0, 4))],
                                delgado={"espesor": 1, "ubicacion": "centro"}), math.pi * (5.5 ** 2 - 4.5 ** 2) * 4)


# ---------------------------------------------------------------- 3. barrido
def test_barrido_recto_distancia_e_inclinacion():
    ruta = [linea((0, 0, 0), (0, 0, 10))]
    c2 = circulo((0, 0, 0), 2)
    valido(sc.barrer([c2], ruta), math.pi * 4 * 10)
    valido(sc.barrer([c2], ruta, distancia=0.5), math.pi * 4 * 5)
    r2 = 2 + 10 * math.tan(math.radians(5))
    valido(sc.barrer([c2], ruta, conicidad=5), math.pi * 10 / 3 * (4 + r2 * r2 + 2 * r2))
    valido(sc.barrer([anillo(0, 3, 1)], ruta), math.pi * 8 * 10)
    superficie = sc.barrer([c2], ruta, solido=False)
    assert g.area(superficie) == pytest.approx(2 * math.pi * 2 * 10, rel=1e-6)


def test_barrido_con_torsion_gira_el_perfil():
    ruta = [linea((0, 0, 0), (0, 0, 10))]
    s = valido(sc.barrer([rect(-2, -0.5, 2, 0.5)], ruta, torsion=90), 40, rel=2e-3)
    tapa = [c for c in g.caras(s) if abs(g.centro_masa(c, superficie=True)[2] - 10) < 1e-6][0]
    (x0, y0, _), (x1, y1, _) = g.caja_envolvente(tapa)
    assert (x1 - x0, y1 - y0) == pytest.approx((1, 4), abs=1e-3)       # la tapa final quedó girada 90°


def test_barrido_por_arco_y_por_esquina():
    arco = BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(20, 0, 0), gp_Pnt(20 * math.sqrt(0.5), 0, 20 * math.sqrt(0.5)),
                                                      gp_Pnt(0, 0, 20)).Value()).Edge()
    valido(sc.barrer([circulo((20, 0, 0), 2)], [arco]), math.pi * 4 * (math.pi / 2 * 20))
    paralelo = valido(sc.barrer([circulo((20, 0, 0), 2)], [arco], orientacion="paralela"), math.pi * 4 * 20)
    assert caja_de(paralelo)[5] == pytest.approx(20)                  # el círculo sigue horizontal
    valido(sc.barrer([circulo((0, 0, 0), 2)], [linea((0, 0, 0), (0, 0, 10)), linea((0, 0, 10), (10, 0, 10))]))


def test_barrido_con_carril_guia():
    ruta = [linea((0, 0, 0), (0, 0, 10))]
    cuadrado = rect(-1, -1, 1, 1)
    # el carril se abre de 1 a 3: el cuadrado escala de lado 2 a 6 (tronco de pirámide)
    valido(sc.barrer([cuadrado], ruta, carril=[linea((1, 0, 0), (3, 0, 10))]), 10 / 3 * (4 + 36 + 12), rel=1e-3)
    valido(sc.barrer([circulo((0, 0, 0), 2)], ruta, carril=[linea((2, 0, 0), (4, 0, 10))]),
           math.pi * 10 / 3 * (4 + 16 + 8), rel=1e-3)
    valido(sc.barrer([cuadrado], ruta, carril=[linea((1, 0, 0), (3, 0, 10))], escala_carril="ninguna"), 40, rel=1e-3)
    with pytest.raises(g.ErrorGeometria):
        sc.barrer([cuadrado], ruta, carril=[linea((1, 0, 0), (3, 0, 10))], torsion=10)


# ---------------------------------------------------------------- 4. solevado
def test_solevado_basico_punto_agujeros_y_cerrado():
    q1, q2 = rect(0, 0, 10, 10), rect(0, 0, 10, 10, 10)
    valido(sc.solevar([q1, q2]), 1000)                                 # dos cuadrados iguales = prisma
    valido(sc.solevar([q1, q2], reglada=True), 1000)
    valido(sc.solevar([q1, (5, 5, 10)]), 1000 / 3)                     # hasta un punto = pirámide
    valido(sc.solevar([anillo(0, 3, 1), anillo(10, 3, 1)]), math.pi * 8 * 10)
    cuadrado = poligono([(9, -1, 0), (11, -1, 0), (11, 1, 0), (9, 1, 0)])
    secciones = [sc.aplicar(cuadrado, t) for t in sc.transformaciones_circulares((0, 0, 0), (0, 1, 0), 4)]
    cerrado = valido(sc.solevar(secciones, cerrada=True))
    assert len(g.solidos(cerrado)) == 1 and g.volumen(cerrado) > 4 * 2 * math.pi * 9
    with pytest.raises(g.ErrorGeometria):
        sc.solevar([q1, (5, 5, 5), q2])


def test_solevado_con_linea_central_y_carril():
    secciones = [circulo((0, 0, 0), 2), circulo((0, 0, 10), 3)]
    cono = math.pi * 10 / 3 * (4 + 9 + 6)
    valido(sc.solevar(secciones, linea_central=[linea((0, 0, 0), (0, 0, 10))]), cono, rel=1e-4)
    valido(sc.solevar(secciones, carriles=[linea((2, 0, 0), (3, 0, 10))]), cono, rel=1e-4)
    with pytest.raises(g.ErrorGeometria):
        sc.solevar(secciones, carriles=[linea((2, 0, 0), (3, 0, 10)), linea((-2, 0, 0), (-3, 0, 10))])


def octogono(radio, z):
    return poligono([(radio * math.cos(k * math.pi / 4), radio * math.sin(k * math.pi / 4), z) for k in range(8)])


def _tipos(forma, tipo):
    firmas = [rf.firma(s) for s in rf.subformas(forma, tipo)]
    return firmas, {f["geom"] for f in firmas}


@pytest.mark.parametrize("reglada", [False, True])
def test_solevado_entre_poligonos_da_caras_planas(reglada):
    """Hallazgo L196/L197: las caras laterales salían B-spline (sin normal: no se podía bocetar ni ubicar agujeros
    sobre ellas) y el vaciado de ese loft mezclaba caras planas y «otra». Tronco de octógonos (A = 2√2·R²)."""
    a1, a2 = 2 * math.sqrt(2) * 50 ** 2, 2 * math.sqrt(2) * 40 ** 2
    tronco = valido(sc.solevar([octogono(50, 0), octogono(40, 100)], reglada=reglada),
                    100 / 3 * (a1 + a2 + math.sqrt(a1 * a2)))                    # 575.113,5
    caras, tipos = _tipos(tronco, "cara")
    assert len(caras) == 10 and tipos == {"plano"}
    for f in caras:                        # normales hacia afuera: tapas ∓Z, laterales alejándose del eje
        c, n = np.array(f["centro"]), np.array(f["normal"])
        if abs(n[2]) > 0.99:
            assert n[2] * (c[2] - 50) > 0
        else:
            assert float(n[:2] @ c[:2]) > 0
    assert _tipos(tronco, "arista")[1] == {"linea"}
    arriba = [c for c in g.caras(tronco) if abs(g.centro_masa(c, superficie=True)[2] - 100) < 1e-6]
    hueco = sm.vaciado(tronco, arriba, espesor_interior=3.0)
    assert g.es_valida(hueco) and _tipos(hueco, "cara")[1] == {"plano"} and len(g.caras(hueco)) == 19


def test_solevado_entre_circulos_da_aristas_circulares():
    """Hallazgo L176: las aristas de sección salían B-spline y la rosca, los agujeros, las uniones y las fijaciones
    (que buscan aristas circulares) no las veían. La costura sigue siendo B-spline."""
    secciones = [(r, z) for r, z in ((30, 0), (30, 100), (20, 150), (10, 180))]
    botella = valido(sc.solevar([circulo((0, 0, z), r) for r, z in secciones]))
    cruda = sc._loft([("alambre", alambre_circulo((0, 0, z), r)) for r, z in secciones], True, False, False)
    assert g.volumen(botella) == pytest.approx(g.volumen(cruda), rel=1e-12)     # la misma forma
    aristas, tipos = _tipos(botella, "arista")
    circulos = sorted((f for f in aristas if f["geom"] == "circulo"), key=lambda f: f["centro"][2])
    assert [f["radio"] for f in circulos] == pytest.approx([30, 10], rel=1e-8)     # ajuste de OCC: 30,00000002
    assert np.allclose([f["centro"] for f in circulos], [(0, 0, 0), (0, 0, 180)], atol=1e-7)
    assert [f["largo"] for f in circulos] == pytest.approx([60 * math.pi, 20 * math.pi], rel=1e-8)
    assert sum(f["geom"] == "bspline" for f in aristas) == 1


def test_referencia_vieja_de_solevado_resuelve_a_la_cara_y_arista_canonicas():
    """Los .omnicad guardados antes tienen las firmas de esas caras y aristas como 'bspline' (sin normal, radio ni
    centro): tienen que seguir resolviendo a la misma subforma, ahora plana o circular. Antes, una arista circular
    vieja de la botella resolvía a la costura (la única B-spline que quedaba). Al revés sigue estricto."""
    for forma in (sc.solevar([octogono(50, 0), octogono(40, 100)]),
                  sc.solevar([circulo((0, 0, z), r) for r, z in ((30, 0), (30, 100), (20, 150), (10, 180))])):
        for tipo, quitar in (("cara", ("normal",)), ("arista", ("radio", "centro"))):
            for sub in rf.subformas(forma, tipo):
                ref = rf.referencia("c1", sub, forma=forma)
                if ref["firma"]["geom"] not in ("plano", "linea", "circulo"):
                    continue
                vieja = {k: v for k, v in ref["firma"].items() if k not in quitar}
                assert rf.resolver(forma, dict(ref, firma=dict(vieja, geom="bspline"))).IsSame(sub)
                otra = dict(ref, firma=dict(ref["firma"], geom="cilindro" if tipo == "cara" else "elipse"))
                assert rf.resolver(forma, otra) is None


# ---------------------------------------------------------------- 5. nervio y red
def test_nervio_hasta_el_cuerpo_y_con_profundidad():
    canal = canal_u()
    # línea a z=8 en el plano y=10: crece hacia el piso y se extiende hasta las paredes
    s = valido(sc.nervio(canal, [linea((10, 10, 8), (30, 10, 8))], (0, 1, 0), 2.0), 36 * 6 * 2)
    assert caja_de(s) == pytest.approx([2, 9, 2, 38, 11, 8])
    valido(sc.nervio(canal, [linea((10, 10, 8), (30, 10, 8))], (0, 1, 0), 2.0, profundidad=3), 36 * 3 * 2)
    s = valido(sc.nervio(canal, [linea((10, 10, 8), (30, 10, 8))], (0, 1, 0), 2.0, direccion="lado1"), 36 * 6 * 2)
    assert caja_de(s)[1:5:3] == pytest.approx([10, 12])


def test_red_hasta_el_piso():
    canal = canal_u()
    s = valido(sc.red(canal, [linea((5, 10, 12), (35, 10, 12))], Z, 2.0), 36 * 10 * 2)
    assert caja_de(s) == pytest.approx([2, 9, 2, 38, 11, 12])
    cruz = sc.red(canal, [linea((5, 10, 12), (35, 10, 12)), linea((20, 5, 12), (20, 15, 12))], Z, 2.0)
    valido(cruz, 36 * 10 * 2 + 20 * 10 * 2 - 2 * 2 * 10)


# ---------------------------------------------------------------- 6. repujado
def test_repujado_plano_relieve_grabado_y_limite_de_cara():
    caja = g.caja(40, 20, 10)
    tapa = cara_superior(caja, 10)
    perfil = rect(5, 5, 15, 15, 20)                                    # boceto en un plano paralelo más arriba
    valido(sc.repujado(caja, [perfil], tapa, 1.5), 8000 + 150)
    valido(sc.repujado(caja, [perfil], tapa, 1.5, tipo="grabado"), 8000 - 150)
    valido(sc.repujado(caja, [perfil], tapa, -1.5), 8000 - 150)       # profundidad negativa = grabado
    valido(sc.repujado(caja, [rect(35, 5, 45, 15, 20)], tapa, 1.0), 8000 + 50)   # se limita a la cara


def test_repujado_envolviendo_un_cilindro():
    cil = g.cilindro(10, 30)
    lateral = [c for c in g.caras(cil) if g.plano_de_cara(c) is None][0]
    boceto = poligono([(10, -2, 12), (10, 2, 12), (10, 2, 18), (10, -2, 18)])   # plano tangente x = 10
    base = math.pi * 100 * 30
    sector = (4 / 10) / 2 * 6                                          # ángulo/2 · alto: área del sector por r²
    s = valido(sc.repujado(cil, [boceto], lateral, 1.0, envolver=True), base + sector * (121 - 100))
    assert caja_de(s)[3] == pytest.approx(11)
    valido(sc.repujado(cil, [boceto], lateral, 1.0, tipo="grabado", envolver=True), base - sector * (100 - 81))
    with pytest.raises(g.ErrorGeometria):
        sc.repujado(cil, [boceto], lateral, 1.0)


# ---------------------------------------------------------------- 7. agujeros
def test_agujeros_simple_ciego_abocardado_y_avellanado():
    caja = g.caja(20, 20, 10)
    arriba, abajo = (10, 10, 10), (0, 0, -1)
    pasante = valido(sc.agujero(caja, arriba, abajo, diametro=6))
    valido(g.booleano(caja, pasante, "cortar"), 4000 - math.pi * 9 * 10)          # caja − cilindro
    ciego = sc.agujero(caja, arriba, abajo, diametro=6, profundidad=5)
    punta = math.pi * 9 * (3 / math.tan(math.radians(59))) / 3                    # cono de 118°
    valido(g.booleano(caja, ciego, "cortar"), 4000 - math.pi * 9 * 5 - punta)
    plano = sc.agujero(caja, arriba, abajo, diametro=6, profundidad=5, punta="plana")
    valido(g.booleano(caja, plano, "cortar"), 4000 - math.pi * 9 * 5)
    abocardado = sc.agujero(caja, arriba, abajo, tipo="abocardado", diametro=6, diam_abocardado=10, prof_abocardado=3)
    valido(g.booleano(caja, abocardado, "cortar"), 4000 - math.pi * 9 * 7 - math.pi * 25 * 3)
    avellanado = sc.agujero(caja, arriba, abajo, tipo="avellanado", diametro=6, diam_avellanado=12)
    valido(g.booleano(caja, avellanado, "cortar"), 4000 - math.pi * 9 * 7 - math.pi * 3 / 3 * (36 + 9 + 18))
    with pytest.raises(g.ErrorGeometria):
        sc.agujero(caja, arriba, abajo, tipo="abocardado", diametro=6, diam_abocardado=4, prof_abocardado=3)


# ---------------------------------------------------------------- 8. roscas
def test_tabla_de_roscas():
    assert len([k for k in sc.TABLA_ROSCAS if sc.TABLA_ROSCAS[k]["norma"] == "ISO métrica gruesa"]) == 29
    m6 = sc.datos_rosca("M6")
    assert (m6["designacion"], m6["paso"], m6["broca"]) == ("M6x1", 1.0, 5.0)
    assert m6["diametro_menor"] == pytest.approx(6 - 1.082532, abs=1e-5)
    assert sc.datos_rosca("m10 x 1.25")["paso"] == 1.25
    assert sc.datos_rosca("M64")["paso"] == 6.0 and sc.datos_rosca("M1.6")["paso"] == 0.35
    unc = sc.datos_rosca("1/4-20")
    assert unc["designacion"] == "1/4-20 UNC" and unc["diametro"] == pytest.approx(6.35)
    assert sc.datos_rosca("#10-32 UNF")["paso"] == pytest.approx(25.4 / 32)
    with pytest.raises(g.ErrorGeometria):
        sc.datos_rosca("M7")


@pytest.mark.parametrize("designacion", ["M6", "M10", "M20"])
def test_rosca_exterior_modelada(designacion):
    dat = sc.datos_rosca(designacion)
    d, d1 = dat["diametro"], dat["diametro_menor"]
    cuerpo = g.cilindro(d / 2, 10)
    t = time.perf_counter()
    roscado = sc.rosca(cuerpo, longitud=6)
    assert time.perf_counter() - t < 5
    assert g.es_valida(roscado) and len(g.solidos(roscado)) == 1
    v_nucleo, v_mayor = math.pi * (d1 / 2) ** 2 * 10, math.pi * (d / 2) ** 2 * 10
    assert v_nucleo < g.volumen(roscado) < v_mayor
    # el surco ocupa ~9/16 del anillo entre núcleo y diámetro mayor en el tramo roscado
    quitado = v_mayor - g.volumen(roscado)
    assert quitado == pytest.approx(9 / 16 * math.pi * ((d / 2) ** 2 - (d1 / 2) ** 2) * 6, rel=0.05)


@pytest.mark.parametrize("designacion", ["M6", "M10", "M20"])
def test_rosca_interior_modelada(designacion):
    dat = sc.datos_rosca(designacion)
    d, d1 = dat["diametro"], dat["diametro_menor"]
    bloque = g.booleano(g.caja(2 * d, 2 * d, 8, (-d, -d, 0)), g.cilindro(d1 / 2, 8), "cortar")
    t = time.perf_counter()
    roscado = sc.rosca(bloque, designacion=designacion)
    assert time.perf_counter() - t < 5
    assert g.es_valida(roscado)
    quitado = g.volumen(bloque) - g.volumen(roscado)
    # el filete del tornillo ocupa ~7/16 del anillo entre D1 y D (con M10 y M20 el corte directo fallaba)
    assert quitado == pytest.approx(7 / 16 * math.pi * ((d / 2) ** 2 - (d1 / 2) ** 2) * 8, rel=0.05)


def test_agujero_roscado_y_rosca_cosmetica():
    caja = g.caja(16, 16, 10, (-8, -8, 0))
    herramienta = sc.agujero(caja, (0, 0, 10), (0, 0, -1), roscado="M8")
    resultado = g.booleano(caja, herramienta, "cortar")
    d1 = sc.datos_rosca("M8")["diametro_menor"]
    sin_rosca = g.volumen(caja) - math.pi * (d1 / 2) ** 2 * 10
    assert g.es_valida(resultado) and g.volumen(resultado) < sin_rosca - 1.0
    cil = g.cilindro(3, 10)
    assert g.volumen(sc.rosca(cil, modelada=False)) == pytest.approx(g.volumen(cil))
    with pytest.raises(g.ErrorGeometria):
        sc.rosca(cil, designacion="M6", longitud=20)


def test_rosca_en_varios_agujeros_iguales_reusa_el_surco(monkeypatch):
    """Hallazgo L138: M3x0.5 en 4 agujeros de 10 mm tardaba 30 s. El barrido se arma una sola vez y se copia."""
    sc._surco_en_origen.cache_clear()
    llamadas = []
    original = sc._barrido_helicoidal
    monkeypatch.setattr(sc, "_barrido_helicoidal", lambda *a: llamadas.append(1) or original(*a))
    dat = sc.datos_rosca("M3x0.5")
    d, d1 = dat["diametro"], dat["diametro_menor"]
    placa = g.caja(40, 40, 12, (-20, -20, 0))
    centros = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
    for cx, cy in centros:
        placa = g.booleano(placa, g.cilindro(d1 / 2, 10, base=(cx, cy, 2)), "cortar")
    tiempo, quitados = 0.0, []
    for cx, cy in centros:
        cara = next(c for c in sc._caras_cilindricas(placa)
                    if np.allclose(g.centro_masa(c, superficie=True)[:2], (cx, cy), atol=1e-6))
        v = g.volumen(placa)
        t = time.perf_counter()
        placa = sc.rosca(placa, cara, designacion="M3x0.5")
        tiempo += time.perf_counter() - t
        quitados.append(v - g.volumen(placa))
    assert tiempo < 10
    assert len(llamadas) == 1
    assert g.es_valida(placa) and len(g.solidos(placa)) == 1
    assert quitados == pytest.approx([quitados[0]] * 4, rel=1e-4)
    assert quitados[0] == pytest.approx(7 / 16 * math.pi * ((d / 2) ** 2 - (d1 / 2) ** 2) * 10, rel=0.05)


def test_corte_helicoidal_que_no_toca_el_cuerpo_avisa():
    placa = g.caja(40, 40, 12, (-20, -20, 0))
    lejos = sc._surco_rosca((500, 500, 500), (0, 0, 1), 3.0, 0.5, 0.0, 10.0, True, "derecha", radio_cara=1.2)
    with pytest.raises(g.ErrorGeometria):
        sc._cortar_helicoidal(placa, lejos)


# ---------------------------------------------------------------- 8b. familias, clases y holgura de rosca
def test_recetas_viejas_de_rosca_y_agujero_dan_el_mismo_volumen():
    """Volúmenes medidos con el código de antes de las familias de rosca (perfil básico ISO/UN de 60°): las recetas
    viejas tienen que dar EXACTAMENTE la misma geometría (mismas cuentas, misma caché)."""
    sc._surco_en_origen.cache_clear()
    cil = g.cilindro(3, 10)
    assert g.volumen(sc.rosca(cil, longitud=6)) == pytest.approx(250.84060112026796, rel=1e-9)
    assert g.volumen(sc.rosca(cil, designacion="M6", longitud=6, mano="izquierda")) == pytest.approx(
        250.84066914546972, rel=1e-9)


def test_recetas_viejas_de_agujero_roscado_y_rosca_interior_dan_el_mismo_volumen():
    caja = g.caja(16, 16, 10, (-8, -8, 0))
    h = sc.herramienta_agujero((0, 0, 10), (0, 0, -1), roscado="M8", profundidad=6)
    assert g.volumen(g.booleano(caja, h, "cortar")) == pytest.approx(2288.7455586392284, rel=1e-9)
    dd = sc.datos_rosca("1/4-20 UNC")
    blo = g.booleano(g.caja(14, 14, 8, (-7, -7, 0)), g.cilindro(dd["diametro_menor"] / 2, 8), "cortar")
    assert g.volumen(sc.rosca(blo, designacion="1/4-20 UNC")) == pytest.approx(1370.912302636908, rel=1e-9)


def test_familias_de_rosca_con_datos_de_sus_normas():
    assert set(sc.FAMILIAS_ROSCA) == {"iso_metrica", "unificada", "trapezoidal", "acme", "bsp_paralela", "bsp_conica",
                                      "npt"}
    from omnicad.timeline.ops_solido import FAMILIAS_ROSCA
    assert FAMILIAS_ROSCA == tuple(sc.FAMILIAS_ROSCA)
    tr = sc.datos_rosca("Tr20x4")                                            # ISO 2904: d2 = d − P/2, D1 = d − P
    assert (tr["familia"], tr["angulo"], tr["diametro_flancos"], tr["diametro_menor"]) == ("trapezoidal", 30, 18, 16)
    assert sc.datos_rosca("tr 20")["designacion"] == "Tr20x4"
    acme = sc.datos_rosca("1/2-10 ACME")                                     # ASME B1.5: 29°, alto P/2
    assert acme["angulo"] == 29 and acme["diametro_flancos"] == pytest.approx(12.7 - 1.27)
    g12 = sc.datos_rosca("G1/2")                                             # ISO 228-1: 20,955 / 18,631, 14 hilos
    assert g12["diametro"] == 20.955 and g12["paso"] == pytest.approx(25.4 / 14)
    assert g12["diametro_menor"] == pytest.approx(18.631, abs=1e-3) and g12["angulo"] == 55
    assert sc.datos_rosca("Rc 1/2")["designacion"] == "R1/2" and sc.datos_rosca("R1/2")["conica"]
    npt = sc.datos_rosca("1/2 NPT")                                          # B1.20.1: E1 = 0,77843 in
    assert npt["designacion"] == "1/2-14 NPT" and npt["diametro_flancos"] == pytest.approx(0.77843 * 25.4, abs=1e-3)
    assert npt["conicidad"] == pytest.approx(1 / 16)
    assert sc.datos_rosca("#12-24")["diametro"] == pytest.approx(0.216 * 25.4)
    assert sc.datos_rosca("1-1/2-6 UNC")["paso"] == pytest.approx(25.4 / 6)
    assert sc.designaciones_rosca("iso_metrica", "M10") == ["M10x1.5", "M10x1.25", "M10x1"]
    assert sc.tamanos_rosca("trapezoidal")[:3] == ["Tr8", "Tr10", "Tr12"]
    for clave in sc.TABLA_ROSCAS:                                            # toda la tabla se vuelve a leer
        assert sc.datos_rosca(clave)["designacion"] == clave
    with pytest.raises(g.ErrorGeometria):
        sc.datos_rosca("Tr21x4")


def test_paso_libre_iso_273():
    assert sc.diametro_paso_libre("M8") == 9.0
    assert sc.diametro_paso_libre("M8x1.25", "fino") == 8.4 and sc.diametro_paso_libre("M8", "grueso") == 10.0
    assert sc.diametro_paso_libre("M3", "normal") == 3.4 and sc.diametro_paso_libre("M64", "grueso") == 74.0
    with pytest.raises(g.ErrorGeometria):
        sc.diametro_paso_libre("1/4-20")


@pytest.mark.parametrize("designacion", ["Tr20x4", "1/2-10 ACME", "G1/2"])
def test_roscas_de_otras_familias_modeladas(designacion):
    """Perfil de su norma (30°, 29° o 55°): el surco de un perfil simétrico ocupa la mitad del anillo entre el
    diámetro mayor y el menor (exterior e interior)."""
    dat = sc.datos_rosca(designacion)
    d, d1 = dat["diametro"], dat["diametro_menor"]
    largo = 3 * dat["paso"]
    cil = g.cilindro(d / 2, largo + 4)
    exterior = sc.rosca(cil, designacion=designacion, longitud=largo)
    anillo = math.pi * ((d / 2) ** 2 - (d1 / 2) ** 2) * largo
    assert g.es_valida(exterior) and len(g.solidos(exterior)) == 1
    assert g.volumen(cil) - g.volumen(exterior) == pytest.approx(0.5 * anillo, rel=0.03)
    bloque = g.booleano(g.caja(2 * d, 2 * d, largo, (-d, -d, 0)), g.cilindro(d1 / 2, largo), "cortar")
    interior = sc.rosca(bloque, designacion=designacion)
    assert g.es_valida(interior)
    assert g.volumen(bloque) - g.volumen(interior) == pytest.approx(0.5 * anillo, rel=0.03)


def test_rosca_con_clase():
    d1 = sc.datos_rosca("M10")["diametro_menor"]
    cil = g.cilindro(5, 10)
    basica = g.volumen(cil) - g.volumen(sc.rosca(cil, designacion="M10", longitud=6))
    con_6g = g.volumen(cil) - g.volumen(sc.rosca(cil, designacion="M10", longitud=6, clase="6g"))
    # 6g corre todo el perfil δ = (0,032 + 0,132/2)/2 = 0,049 mm hacia el eje: el surco gana 2·δ·tan30° de ancho
    # entre el núcleo y el cilindro, más una franja de δ de alto y P/4 de ancho en el fondo (por vuelta de 1,5 mm)
    delta = (0.032 + 0.132 / 2) / 2
    area = 2 * delta * math.tan(math.radians(30)) * (5 - d1 / 2) + delta * 1.5 / 4
    assert con_6g - basica == pytest.approx(area * 2 * math.pi * (5 + d1 / 2) / 2 * 6 / 1.5, rel=0.05)
    with pytest.raises(g.ErrorGeometria):
        sc.rosca(cil, designacion="M10", longitud=6, clase="6H")              # clase de agujero en un eje


def test_rosca_con_holgura_para_imprimir():
    cil = g.cilindro(5, 8)
    con_6g = g.volumen(cil) - g.volumen(sc.rosca(cil, designacion="M10", longitud=4.5, clase="6g"))
    holgada = g.volumen(cil) - g.volumen(sc.rosca(cil, designacion="M10", longitud=4.5, clase="6g", holgura=0.1))
    assert holgada > con_6g + 1.0
    with pytest.raises(g.ErrorGeometria):
        sc.rosca(cil, designacion="M10", longitud=4.5, holgura=0.5)           # más que la mitad del filete
    # M3 con holgura 0,12: la cresta queda sin espesor y se tornea (antes el surco se tocaba consigo mismo). Se va
    # el 84 % del anillo entre el diámetro menor y el mayor (cuenta a mano del perfil corrido 0,12 mm).
    d1 = sc.datos_rosca("M3")["diametro_menor"]
    bloque = g.booleano(g.caja(6, 6, 3, (-3, -3, 0)), g.cilindro(d1 / 2, 3), "cortar")
    roscado = sc.rosca(bloque, designacion="M3", holgura=0.12)
    assert g.es_valida(roscado)
    assert g.volumen(bloque) - g.volumen(roscado) == pytest.approx(0.84 * math.pi * (1.5 ** 2 - (d1 / 2) ** 2) * 3,
                                                                   rel=0.05)


def test_agujero_roscado_con_clase_y_conico():
    assert sc.diametro_taladro_rosca("M10") == pytest.approx(8.376, abs=1e-3)
    assert sc.diametro_taladro_rosca("M10", "6H") == pytest.approx(8.376 + 0.150, abs=1e-3)   # D1 + TD1/2
    assert sc.diametro_taladro_rosca("M10", "6H", 0.1) == pytest.approx(8.726, abs=1e-3)
    h = sc.herramienta_agujero((0, 0, 20), (0, 0, -1), roscado="M10", clase="6H", profundidad=10, punta="plana")
    basico = sc.herramienta_agujero((0, 0, 20), (0, 0, -1), roscado="M10", profundidad=10, punta="plana")
    assert g.es_valida(h)

    def herramienta_esperada(r_agujero, desfase):
        """Cilindro del agujero + la parte del filete del tornillo que queda afuera: (L/P)·∫ w(ρ)·2πρ dρ, con el
        ancho del filete w(ρ) = P/2 − 2·(ρ − d2/2 − desfase)·tan 30° hasta el diámetro mayor corrido."""
        d2, n = 10 - 0.75 * math.sqrt(3) / 2 * 1.5, 2000
        r_fin = 5 + desfase
        paso_r = (r_fin - r_agujero) / n
        integral = sum((0.75 - 2 * (r - d2 / 2 - desfase) * math.tan(math.radians(30))) * 2 * math.pi * r * paso_r
                       for r in (r_agujero + (k + 0.5) * paso_r for k in range(n)))
        return math.pi * r_agujero ** 2 * 10 + 10 / 1.5 * integral
    # 6H: agujero Ø8,526 (D1 + TD1/2) y flancos corridos (TD2/2)/2 = 0,045 mm
    assert g.volumen(h) == pytest.approx(herramienta_esperada(8.5262 / 2, 0.045), rel=1e-4)
    assert g.volumen(basico) == pytest.approx(herramienta_esperada(sc.datos_rosca("M10")["diametro_menor"] / 2, 0),
                                              rel=1e-4)
    r = sc.datos_rosca("R1/2")["diametro_menor"] / 2                         # cono 1:16 desde la boca
    cono = sc.herramienta_agujero((0, 0, 20), (0, 0, -1), diametro=2 * r, conicidad=1 / 16, profundidad=15,
                                  punta="plana")
    r1 = r - 15 / 32
    assert g.volumen(cono) == pytest.approx(math.pi * 15 / 3 * (r * r + r * r1 + r1 * r1), rel=1e-6)
    assert g.es_valida(cono)
    with pytest.raises(g.ErrorGeometria):
        sc.herramienta_agujero((0, 0, 20), (0, 0, -1), roscado="R1/2", profundidad=10)


def test_agujero_hasta_y_por_referencias():
    caja = g.caja(40, 30, 20)
    arriba = next(c for c in g.caras(caja) if g.plano_de_cara(c) is not None
                  and np.allclose(g.plano_de_cara(c).normal, Z) and g.centro_masa(c, superficie=True)[2] > 19)
    abajo = next(c for c in g.caras(caja) if g.centro_masa(c, superficie=True)[2] < 1e-6)
    assert sc.profundidad_hasta((5, 5, 20), (0, 0, -1), abajo) == pytest.approx(20)
    assert sc.profundidad_hasta((5, 5, 20), (0, 0, -1), g.Plano("XY", 4), desfase=1) == pytest.approx(17)
    assert sc.profundidad_hasta((5, 5, 25), (0, 0, -1), caja) == pytest.approx(5)          # primer corte del cuerpo
    with pytest.raises(g.ErrorGeometria):
        sc.profundidad_hasta((5, 5, 20), (1, 0, 0), g.Plano("XY"))
    aristas = [e for e in rf.subformas(caja, "arista")
               if np.allclose(rf.firma_arista(e)["medio"][2], 20) and rf.firma_arista(e)["geom"] == "linea"]

    def arista_en(eje, valor):
        return next(e for e in aristas if np.allclose([q[eje] for q in rf.firma_arista(e)["extremos"]], valor))
    p = sc.punto_por_referencias(arriba, [arista_en(0, 0), arista_en(1, 0)], [7, 4])
    assert p == pytest.approx([7, 4, 20])
    p = sc.punto_por_referencias(arriba, [arista_en(0, 40), arista_en(1, 30)], [7, 4])   # hacia adentro de la cara
    assert p == pytest.approx([33, 26, 20])
    with pytest.raises(g.ErrorGeometria):
        sc.punto_por_referencias(arriba, [arista_en(0, 0), arista_en(0, 40)], [7, 4])   # paralelas


# ---------------------------------------------------------------- 9. bobina
def test_bobina_secciones_y_posiciones():
    # Pappus para un barrido helicoidal: área de la sección · 2π · radio del centroide · vueltas (la hélice
    # es una B-spline aproximada: tolerancia 1e-5)
    valido(sc.bobina((0, 0, 0), Z, diametro=20, revoluciones=5, paso=5, tamano_seccion=2),
           math.pi * 1 * 2 * math.pi * 10 * 5, rel=1e-5)
    a = math.sqrt(2)
    s = valido(sc.bobina((0, 0, 0), Z, diametro=20, revoluciones=3, altura=15, tamano_seccion=2, seccion="cuadrada",
                         posicion_seccion="dentro"), a * a * 2 * math.pi * (10 - a / 2) * 3, rel=1e-5)
    assert caja_de(s)[3] == pytest.approx(10, abs=1e-3)                # "dentro": no pasa el diámetro
    area_tri = 3 * math.sqrt(3) / 4
    valido(sc.bobina((0, 0, 0), Z, diametro=20, altura=12, paso=4, tamano_seccion=2, seccion="triangular_externa",
                     posicion_seccion="fuera"), area_tri * 2 * math.pi * 10.5 * 3, rel=1e-5)
    valido(sc.bobina((0, 0, 0), (1, 0, 0), diametro=10, revoluciones=2, paso=3, tamano_seccion=1, horario=True),
           math.pi * 0.25 * 2 * math.pi * 5 * 2, rel=1e-5)
    conica = valido(sc.bobina((0, 0, 0), Z, diametro=20, revoluciones=4, paso=5, tamano_seccion=2, angulo=10))
    assert caja_de(conica)[3] > 13
    with pytest.raises(g.ErrorGeometria):
        sc.bobina((0, 0, 0), Z, diametro=20, revoluciones=5, tamano_seccion=2)
    with pytest.raises(g.ErrorGeometria):
        sc.bobina((0, 0, 0), Z, diametro=20, revoluciones=5, paso=1, tamano_seccion=2)


# ---------------------------------------------------------------- 10. tubería
def test_tuberia_maciza_hueca_y_secciones():
    ruta = [linea((0, 0, 0), (0, 0, 10))]
    valido(sc.tuberia(ruta, tamano=4), math.pi * 4 * 10)
    valido(sc.tuberia(ruta, tamano=4, hueca=True, espesor=0.5), math.pi * (4 - 2.25) * 10)
    valido(sc.tuberia(ruta, tamano=4, seccion="cuadrada"), 8 * 10)
    ri = 2 - 0.3 / math.cos(math.pi / 3)
    valido(sc.tuberia(ruta, tamano=4, seccion="triangular", hueca=True, espesor=0.3),
           3 * math.sqrt(3) / 4 * (4 - ri * ri) * 10)
    valido(sc.tuberia([linea((0, 0, 0), (0, 0, 10)), linea((0, 0, 10), (10, 0, 10))], tamano=2, distancia=0.5),
           math.pi * 10)


# ---------------------------------------------------------------- 11. patrones y simetría
def traslaciones(ts):
    return [tuple(np.round(sc.a_matriz(t)[:3, 3], 6)) for t in ts]


def test_patron_rectangular_extension_espaciado_simetrico_y_suprimir():
    ts = sc.transformaciones_rectangulares((1, 0, 0), 3, 20, (0, 1, 0), 2, 5)
    assert traslaciones(ts) == [(0, 0, 0), (0, 5, 0), (10, 0, 0), (10, 5, 0), (20, 0, 0), (20, 5, 0)]
    ts = sc.transformaciones_rectangulares((1, 0, 0), 3, 5, distribucion="espaciado", simetrico1=True,
                                           suprimir=[(1, 0), (0, 0)])
    assert traslaciones(ts) == [(-10, 0, 0), (-5, 0, 0), (0, 0, 0), (10, 0, 0)]


def test_patron_circular_de_6_copias():
    ts = sc.transformaciones_circulares((0, 0, 0), Z, 6)
    copias = [sc.aplicar(g.caja(2, 2, 2, (10, -1, 0)), t) for t in ts]
    union = valido(g.unir_todos(copias), 6 * 8)
    assert len(g.solidos(union)) == 6
    angulos = sorted(round(math.degrees(math.atan2(c[1], c[0])) % 360, 6) for c in map(g.centro_masa, copias))
    assert angulos == pytest.approx([0, 60, 120, 180, 240, 300])
    ts = sc.transformaciones_circulares((0, 0, 0), Z, 4, angulo_total=90)
    assert [round(math.degrees(math.atan2(m[1, 0], m[0, 0])), 6) for m in map(sc.a_matriz, ts)] == [0, 30, 60, 90]
    ts = sc.transformaciones_circulares((0, 0, 0), Z, 3, angulo_total=30, distribucion="espaciado", simetrico=True)
    assert len(ts) == 5


def test_patron_en_ruta_identica_y_con_direccion():
    largo = math.pi / 2 * 20
    ts = sc.transformaciones_en_ruta([arco_xy(20)], 3, largo, orientacion="direccion_ruta")
    m = [sc.a_matriz(t) for t in ts]
    destinos = np.array([(mm @ np.array([20, 0, 0, 1.0]))[:3] for mm in m])
    esperados = np.array([(20, 0, 0), (20 * math.sqrt(0.5), 20 * math.sqrt(0.5), 0), (0, 20, 0)])
    assert np.allclose(destinos, esperados, atol=1e-6)
    assert math.degrees(math.atan2(m[-1][1, 0], m[-1][0, 0])) == pytest.approx(90)   # girada con la tangente
    ts = sc.transformaciones_en_ruta([arco_xy(20)], 2, largo / 2, inicio=0.5, simetrico=True)
    assert len(ts) == 3 and all(abs(sc.a_matriz(t)[0, 1]) < 1e-12 for t in ts)          # "identica": sin giro
    ts = sc.transformaciones_en_ruta([arco_xy(20)], 5, largo / 2, distribucion="espaciado")
    assert len(ts) == 3                                                    # las que caen fuera se omiten
    circulo_completo = BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*Z)), 10)).Edge()
    ts = sc.transformaciones_en_ruta([circulo_completo], 4, 2 * math.pi * 10)
    assert np.allclose([sc.a_matriz(t)[:3, 3] for t in ts], [(0, 0, 0), (-10, 10, 0), (-20, 0, 0), (-10, -10, 0)])


def test_simetria_y_aplicar():
    s = valido(sc.simetria(g.caja(2, 3, 4, (5, 0, 0)), g.Plano("YZ")), 24)
    assert caja_de(s) == pytest.approx([-7, 0, 0, -5, 3, 4])
    m = np.eye(4)
    m[:3, 3] = (5, 0, 0)
    assert caja_de(sc.aplicar(g.caja(1, 1, 1), m)) == pytest.approx([5, 0, 0, 6, 1, 1])


# ---------------------------------------------------------------- 12. engrosar
def test_engrosar_caras_un_lado_negativo_simetrico_y_curvo():
    q = rect(0, 0, 10, 10)
    assert caja_de(valido(sc.engrosar([q], 2), 200))[2:6:3] == pytest.approx([0, 2])
    assert caja_de(valido(sc.engrosar([q], -2), 200))[2:6:3] == pytest.approx([-2, 0])
    assert caja_de(valido(sc.engrosar([q], 2, direccion="simetrica"), 200))[2:6:3] == pytest.approx([-1, 1])
    lateral = [c for c in g.caras(g.cilindro(10, 10)) if g.plano_de_cara(c) is None]
    valido(sc.engrosar(lateral, 1), math.pi * (121 - 100) * 10)
    abierta = [c for c in g.caras(g.caja(10, 10, 10)) if g.centro_masa(c, superficie=True)[2] > 1e-6]
    valido(sc.engrosar(abierta, 1))                                     # cáscara cosida de 5 caras


# ---------------------------------------------------------------- 13. relleno de contorno
def test_relleno_de_contorno_celdas_y_seleccion():
    a, b = g.caja(10, 10, 10), g.caja(10, 10, 10, (5, 0, 0))
    celdas = sc.relleno_contorno_celdas([a, b])
    assert [round(c["volumen"], 6) for c in celdas] == [500, 500, 500]
    assert [c["centroide"][0] for c in celdas] == pytest.approx([2.5, 7.5, 12.5])
    valido(sc.relleno_contorno([a, b], [0, 1]), 1000)
    planos = [g.Plano("XY"), g.Plano("XY", 10), g.Plano("XZ"), g.Plano("XZ", -10), g.Plano("YZ"), g.Plano("YZ", 10)]
    assert [round(c["volumen"], 6) for c in sc.relleno_contorno_celdas(planos, tamano_plano=50)] == [1000]
    lateral = [c for c in g.caras(g.cilindro(5, 20, base=(0, 0, -5))) if g.plano_de_cara(c) is None][0]
    valido(sc.relleno_contorno([lateral, g.Plano("XY"), g.Plano("XY", 10)], [0], tamano_plano=50), math.pi * 25 * 10)
    with pytest.raises(g.ErrorGeometria):
        sc.relleno_contorno([a, b], [7])


# ---------------------------------------------------------------- 14. sólido envolvente
def test_solido_envolvente_caja_y_cilindro():
    valido(sc.solido_envolvente([g.caja(10, 20, 30)]), 6000)
    valido(sc.solido_envolvente([g.caja(10, 20, 30)], margen=1), 12 * 22 * 32)
    valido(sc.solido_envolvente([g.cilindro(5, 10)], tipo="cilindro"), math.pi * 25 * 10, rel=1e-5)
    valido(sc.solido_envolvente([g.caja(6, 8, 10)], tipo="cilindro"), math.pi * 25 * 10, rel=1e-5)  # diagonal 10
    valido(sc.solido_envolvente([g.cilindro(5, 10, eje=(1, 0, 0))], tipo="cilindro", eje="x"), math.pi * 25 * 10,
           rel=1e-5)
    valido(sc.solido_envolvente([g.cilindro(5, 10, eje=(1, 1, 0))], tipo="cilindro", eje=(1, 1, 0)),
           math.pi * 25 * 10, rel=1e-4)


# ---------------------------------------------------------------- 15. plástico
def test_saliente_y_labio_ranura():
    hueca = g.booleano(g.caja(40, 40, 20), g.caja(36, 36, 20, (2, 2, 2)), "cortar")   # abierta arriba, piso de 2
    v = g.volumen(hueca)
    valido(sc.saliente(hueca, (20, 20, 20), (0, 0, -1), diametro_exterior=6, diametro_agujero=2.5),
           v + math.pi * (9 - 1.5625) * 18)
    valido(sc.saliente(hueca, (20, 20, 20), (0, 0, -1), diametro_exterior=6, diametro_agujero=2.5, altura=8),
           v + math.pi * (9 - 1.5625) * 8)
    borde = [linea((2, 2, 20), (38, 2, 20)), linea((38, 2, 20), (38, 38, 20)),
             linea((38, 38, 20), (2, 38, 20)), linea((2, 38, 20), (2, 2, 20))]
    labio = valido(sc.labio_ranura(hueca, borde, Z, ancho=1, alto=1.5), v + 4 * 37 * 1 * 1.5)
    assert caja_de(labio)[5] == pytest.approx(21.5)
    valido(sc.labio_ranura(hueca, borde, Z, tipo="ranura", ancho=1, alto=1.5, holgura=0.1), v - 4 * 37.1 * 1.1 * 1.6)
