# -*- coding: utf-8 -*-
"""SUPERFICIE con guías: SUP-9 (primitivas), SUP-12 (barrido con riel, superficie guía y conicidad), SUP-13 (solevación con
condiciones de borde, rieles y línea central) y SUP-21 (bordes de Coser). Cada opción con su número (área, caja o distancia)
y `es_valida`, en el núcleo, en el paso, en el diálogo y en la API."""
import math

import numpy as np
import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepTools import BRepTools
from OCP.GC import GC_MakeArcOfCircle
from OCP.gp import gp_Pnt, gp_Vec
from test_superficie_fusion import app_qt as app_qt  # noqa: F401  (fixture de la QApplication)
from test_superficie_fusion import (_boceto, _curvas, _ejecutar, _hit_cuerpo, _linea, _roundtrip, _ultimo, aristas, caja,
                                    circulo, falla, llamar, seg)

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.nucleo import superficies as sf
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto
from omnicad.timeline.ops_superficie import OpSupBarrido, OpSupPrimitiva, OpSupSolevacion


def arco(a, b, c):
    return BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, b)),
                                                      gp_Pnt(*map(float, c))).Value()).Edge()


def toca(forma, punto, tol=0.05):
    return BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, punto))).Vertex(), forma).Value() < tol


def rectangulo(lado, z=0.0):
    p = [(-lado, -lado, z), (lado, -lado, z), (lado, lado, z), (-lado, lado, z)]
    return [seg(p[i], p[(i + 1) % 4]) for i in range(4)]


def tangente_de_salida(forma, u_rel=0.5):
    """Dirección unitaria con la que la superficie (de una cara) sale de su primera sección, a la fracción u_rel."""
    cara = g.caras(forma)[0]
    u0, u1, v0, _v1 = BRepTools.UVBounds_s(cara)
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    BRepAdaptor_Surface(cara).D1(u0 + (u1 - u0) * u_rel, v0, p, du, dv)
    d = np.array([dv.X(), dv.Y(), dv.Z()])
    return d / np.linalg.norm(d)


RUTA_Z = ((0, 0, 0), (0, 0, 100))
RADIO = ((0, 0, 0), (10, 0, 0))


# ================================================================ SUP-12 barrido
def test_conicidad_de_un_perfil_abierto_da_el_trapecio_exacto():
    f = sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), conicidad=5)
    ensancha = 100 * math.tan(math.radians(5))
    assert g.area(f) == pytest.approx(100 * (10 + 10 + ensancha) / 2, rel=1e-6)
    assert caja(f)[1][0] == pytest.approx(10 + ensancha, abs=1e-3) and g.es_valida(f)


def test_conicidad_de_un_circulo_da_el_tronco_de_cono():
    f = sf.barrer_superficie(circulo(10), seg(*RUTA_Z), conicidad=5)
    r = 10 + 100 * math.tan(math.radians(5))
    assert g.area(f) == pytest.approx(math.pi * (10 + r) * math.hypot(100, r - 10), rel=1e-6) and g.es_valida(f)
    cierra = sf.barrer_superficie(circulo(10), seg(*RUTA_Z), conicidad=-3)
    assert caja(cierra)[1][0] == pytest.approx(10, abs=1e-3) and g.area(cierra) < g.area(sf.barrer_superficie(circulo(10), seg(*RUTA_Z)))


def test_conicidad_con_torsion_se_combinan():
    f = sf.barrer_superficie(circulo(10), seg(*RUTA_Z), conicidad=5, torsion=90)
    assert g.es_valida(f) and caja(f)[1][2] == pytest.approx(100, abs=1e-3)
    assert g.area(f) == pytest.approx(9066.22, rel=2e-3)


def test_conicidad_con_valores_que_no_sirven_dice_por_que():
    with pytest.raises(g.ErrorGeometria, match="desaparece"):
        sf.barrer_superficie(circulo(10), seg(*RUTA_Z), conicidad=-30)
    with pytest.raises(g.ErrorGeometria, match="perpendicular"):
        sf.barrer_superficie(circulo(10), seg(*RUTA_Z), conicidad=5, orientacion="paralela")
    with pytest.raises(g.ErrorGeometria, match="-89"):
        sf.barrer_superficie(circulo(10), seg(*RUTA_Z), conicidad=89)
    with pytest.raises(g.ErrorGeometria, match="-89"):
        sf.barrer_superficie(circulo(10), seg(*RUTA_Z), conicidad=float("nan"))


def test_riel_escalar_y_ninguna():
    riel = seg((10, 0, 0), (20, 0, 100))
    escalar = sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel)
    assert g.area(escalar) == pytest.approx(1500, rel=1e-6) and caja(escalar)[1][0] == pytest.approx(20) and g.es_valida(escalar)
    ninguna = sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, escala="ninguna")
    assert g.area(ninguna) == pytest.approx(1000, rel=1e-6) and g.es_valida(ninguna)


def test_riel_estirar_conserva_la_altura_del_perfil():
    semi = arco((0, 0, 0), (5, 5, 0), (10, 0, 0))
    riel = seg((10, 0, 0), (20, 0, 100))
    escalar = sf.barrer_superficie(semi, seg(*RUTA_Z), carril=riel)
    estirar = sf.barrer_superficie(semi, seg(*RUTA_Z), carril=riel, escala="estirar")
    assert caja(estirar)[1][1] == pytest.approx(5, abs=1e-3) and caja(escalar)[1][1] > 9
    assert caja(estirar)[1][0] == pytest.approx(20, abs=1e-3) and g.es_valida(estirar)
    assert toca(estirar, (20, 0, 100)) and toca(estirar, (15, 0, 50))


def test_riel_estirar_pegado_a_la_ruta_dice_por_que():
    with pytest.raises(g.ErrorGeometria, match="separado"):
        sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=seg((0, 0, 0), (0, 0, 100)), escala="estirar")


def test_extension_perpendicular_corta_el_riel_en_el_plano_del_final():
    riel = seg((10, 0, 0), (20, 0, 100))
    mitad = sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, distancia=0.5)
    assert g.area(mitad) == pytest.approx(50 * 12.5, rel=1e-6) and caja(mitad)[1][2] == pytest.approx(50)
    largo = sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=seg((10, 0, 0), (10, 0, 200)))
    assert g.area(largo) == pytest.approx(1000, rel=1e-6)
    corto = sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=seg((10, 0, 0), (10, 0, 50)))
    assert g.area(corto) == pytest.approx(500, rel=1e-6) and caja(corto)[1][2] == pytest.approx(50, abs=1e-4)


def test_extension_completa_usa_una_fraccion_de_cada_una():
    riel = seg((10, 0, 0), (20, 0, 100))
    f = sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, extension="completa", distancia=0.5, distancia_carril=0.5)
    assert g.area(f) == pytest.approx(625, rel=1e-6)
    with pytest.raises(g.ErrorGeometria, match="distancia"):
        sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, extension="completa", distancia_carril=0)


def test_superficie_guia_con_una_ruta_apoyada_que_no_es_arista_de_ella():
    cilindro = next(c for c in g.caras(g.cilindro(20, 40)) if g.area(c) > 1000)
    k = 20 * math.sqrt(0.5)
    f = sf.barrer_superficie(seg((20, 0, 10), (25, 0, 10)), arco((20, 0, 10), (k, k, 10), (0, 20, 10)), superficie_guia=[cilindro])
    assert g.area(f) == pytest.approx((25 ** 2 - 20 ** 2) * math.pi / 4, rel=1e-6) and g.es_valida(f)


def test_superficie_guia_con_la_ruta_afuera_dice_por_que():
    cilindro = next(c for c in g.caras(g.cilindro(20, 40)) if g.area(c) > 1000)
    with pytest.raises(g.ErrorGeometria, match="sobre la superficie"):
        sf.barrer_superficie(seg(*RADIO), seg((50, 0, 0), (50, 0, 10)), superficie_guia=[cilindro])


def test_riel_o_superficie_no_se_combinan_con_torsion_ni_entre_si():
    riel = seg((10, 0, 0), (20, 0, 100))
    with pytest.raises(g.ErrorGeometria, match="Ruta individual"):
        sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, torsion=10)
    with pytest.raises(g.ErrorGeometria, match="no los dos"):
        sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, superficie_guia=[g.caras(g.caja(1, 1, 1))[0]])
    with pytest.raises(g.ErrorGeometria, match="Escala"):
        sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, escala="xx")
    with pytest.raises(g.ErrorGeometria, match="Extensión"):
        sf.barrer_superficie(seg(*RADIO), seg(*RUTA_Z), carril=riel, extension="xx")


# ================================================================ SUP-13 solevación: condiciones de borde
def test_punto_agudo_da_el_cono_y_punto_tangente_la_cupula():
    cono = sf.solevar_superficie([circulo(10), (0.0, 0.0, 10.0)])
    assert g.area(cono) == pytest.approx(math.pi * 10 * math.hypot(10, 10), rel=1e-6)
    cupula = sf.solevar_superficie([circulo(10), (0.0, 0.0, 10.0)], condicion_fin={"tipo": "punto_tangente"})
    assert g.area(cupula) == pytest.approx(2 * math.pi * 100, rel=2e-3) and g.es_valida(cupula)
    assert caja(cupula)[1][2] == pytest.approx(10, abs=1e-3)
    llena = sf.solevar_superficie([circulo(10), (0.0, 0.0, 10.0)], condicion_fin={"tipo": "punto_tangente", "peso": 2.0})
    assert g.area(llena) > g.area(cupula) * 1.05


def test_direccion_inclina_la_salida_con_el_angulo_y_el_peso():
    secciones = [circulo(10), circulo(10, (0, 0, 30))]
    recta = sf.solevar_superficie(secciones)
    assert g.area(recta) == pytest.approx(2 * math.pi * 10 * 30, rel=1e-6)
    abre = sf.solevar_superficie(secciones, condicion_inicio={"tipo": "direccion", "angulo": 45.0})
    assert caja(abre)[1][0] > 12 and g.es_valida(abre)
    mas = sf.solevar_superficie(secciones, condicion_inicio={"tipo": "direccion", "angulo": 45.0, "peso": 2.0})
    assert caja(mas)[1][0] > caja(abre)[1][0] + 1


def test_direccion_en_un_perfil_abierto_recto_o_curvo():
    recta = sf.solevar_superficie([seg((0, 0, 0), (10, 0, 0)), seg((0, 0, 30), (10, 0, 30))],
                                  condicion_inicio={"tipo": "direccion", "angulo": 45.0})
    assert caja(recta)[0][1] < -3 and caja(recta)[1][0] == pytest.approx(10, abs=1e-3) and g.es_valida(recta)
    otro_lado = sf.solevar_superficie([seg((0, 0, 0), (10, 0, 0)), seg((0, 0, 30), (10, 0, 30))],
                                      condicion_inicio={"tipo": "direccion", "angulo": 135.0})
    assert caja(otro_lado)[1][1] > 3
    curva = sf.solevar_superficie([arco((0, 0, 0), (5, 5, 0), (10, 0, 0)), arco((0, 0, 30), (5, 5, 30), (10, 0, 30))],
                                  condicion_fin={"tipo": "direccion", "angulo": 60.0})
    assert g.es_valida(curva) and caja(curva)[1][2] == pytest.approx(30, abs=1e-3)


def test_direccion_en_un_perfil_de_en_medio():
    secciones = [circulo(10), circulo(10, (0, 0, 20)), circulo(10, (0, 0, 40))]
    f = sf.solevar_superficie(secciones, condiciones_medias={1: {"tipo": "direccion", "angulo": 60.0}})
    assert g.es_valida(f) and g.area(f) != pytest.approx(2 * math.pi * 10 * 40, rel=1e-3)
    with pytest.raises(g.ErrorGeometria, match="Dirección"):
        sf.solevar_superficie(secciones, condiciones_medias={1: {"tipo": "tangente", "cara": g.caras(g.caja(1, 1, 1))[0]}})


def _lamina_y_borde():
    lamina = sf.extruir_superficie(seg((0, 0, 0), (0, 10, 0)), (1, 0, 0), 20)
    return lamina, g.caras(lamina)[0], seg((20, 0, 0), (20, 10, 0))


def test_tangente_sale_siguiendo_a_la_cara_y_libre_no():
    _, cara, borde = _lamina_y_borde()
    lejos = seg((30, 0, 10), (30, 10, 10))
    libre = sf.solevar_superficie([borde, lejos])
    assert tangente_de_salida(libre)[0] == pytest.approx(math.sqrt(0.5), abs=1e-3)
    tangente = sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "tangente", "cara": cara})
    assert tangente_de_salida(tangente)[0] > 0.97 and g.es_valida(tangente)
    assert caja(tangente)[0][2] == pytest.approx(0, abs=0.1)
    suave = sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "suave", "cara": cara})
    assert tangente_de_salida(suave)[0] > 0.97 and g.es_valida(suave)


def test_tangente_en_la_boca_de_un_tubo_extruido():
    """La arista de la boca tiene ubicación: la curva cruda de OCC está en la base."""
    tubo = sf.extruir_superficie(circulo(10), (0, 0, 1), 20)
    boca = next(e for e in aristas(tubo) if caja(e)[0][2] == pytest.approx(20))
    libre = sf.solevar_superficie([boca, circulo(5, (0, 0, 30))])
    cae = sf.solevar_superficie([boca, circulo(5, (0, 0, 30))], condicion_inicio={"tipo": "tangente", "cara": g.caras(tubo)[0]})
    assert abs(tangente_de_salida(cae)[2]) > 0.97 > abs(tangente_de_salida(libre)[2]) and g.es_valida(cae)


def test_suave_sigue_la_curvatura_de_la_cara_mejor_que_tangente():
    medio = 10 * math.sqrt(0.5)
    cuarto = sf.extruir_superficie(arco((10, 0, 0), (medio, medio, 0), (0, 10, 0)), (0, 0, 1), 10)
    borde = next(e for e in aristas(cuarto) if caja(e)[0][0] == pytest.approx(0, abs=1e-6) and caja(e)[1][0] == pytest.approx(0, abs=1e-6))
    lejos = seg((-14, 0, 0), (-14, 0, 10))
    cara = g.caras(cuarto)[0]
    desvio = {}
    for tipo in ("tangente", "suave"):
        f = sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": tipo, "cara": cara})
        c = g.caras(f)[0]
        u0, u1, v0, v1 = BRepTools.UVBounds_s(c)
        q = BRepAdaptor_Surface(c).Value((u0 + u1) / 2, v0 + (v1 - v0) * 0.1)
        desvio[tipo] = abs(math.hypot(q.X(), q.Y()) - 10)
    assert desvio["suave"] < desvio["tangente"]


def test_alineacion_de_bordes_en_una_cara_que_no_es_rectangular():
    """Trapecio: su lado llega inclinado al perfil. Align Edges lo continúa; Free Edges sale perpendicular."""
    t = [(0, 0, 0), (20, 2, 0), (20, 8, 0), (0, 10, 0)]
    trapecio = sf.parche([seg(t[i], t[(i + 1) % 4]) for i in range(4)])
    borde = next(e for e in aristas(trapecio) if caja(e)[0][0] == pytest.approx(20) and caja(e)[1][0] == pytest.approx(20))
    lejos = seg((30, 2, 5), (30, 8, 5))
    cara = g.caras(trapecio)[0]
    libre = sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "tangente", "cara": cara, "alineacion": "libre"})
    alinear = sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "tangente", "cara": cara, "alineacion": "alinear"})
    assert g.es_valida(libre) and g.es_valida(alinear)
    y_libre = [abs(tangente_de_salida(libre, s)[1]) for s in (0.0, 1.0)]
    y_alinear = [abs(tangente_de_salida(alinear, s)[1]) for s in (0.0, 1.0)]
    assert max(y_libre) < 0.01 and min(y_alinear) > 0.09        # el lado del trapecio: 2 de 20
    superficie = sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "tangente", "cara": cara, "alineacion": "superficie"})
    assert g.es_valida(superficie) and caja(superficie)[1][2] == pytest.approx(5, abs=0.1)


def test_alineacion_y_condiciones_que_no_valen_dicen_por_que():
    _, cara, borde = _lamina_y_borde()
    lejos = seg((30, 0, 10), (30, 10, 10))
    with pytest.raises(g.ErrorGeometria, match="Alineación"):
        sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "tangente", "cara": cara, "alineacion": "xx"})
    with pytest.raises(g.ErrorGeometria, match="extremos"):
        tubo = sf.extruir_superficie(circulo(10), (0, 0, 1), 20)
        sf.solevar_superficie([next(e for e in aristas(tubo) if caja(e)[0][2] == pytest.approx(20)), circulo(5, (0, 0, 40))],
                              condicion_inicio={"tipo": "tangente", "cara": g.caras(tubo)[0], "alineacion": "alinear"})
    with pytest.raises(g.ErrorGeometria, match="necesita la cara"):
        sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "suave"})
    with pytest.raises(g.ErrorGeometria, match="peso"):
        sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "direccion", "peso": 0.0})
    with pytest.raises(g.ErrorGeometria, match="ángulo"):
        sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "direccion", "angulo": 0.0})
    with pytest.raises(g.ErrorGeometria, match="punto"):
        sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "punto_tangente"})
    with pytest.raises(g.ErrorGeometria, match="desconocida"):
        sf.solevar_superficie([borde, lejos], condicion_inicio={"tipo": "xx"})


def test_una_condicion_no_se_combina_con_rieles_cerrado_ni_tramos_rectos():
    a, b = circulo(10), circulo(10, (0, 0, 30))
    cond = {"tipo": "direccion", "angulo": 60.0}
    with pytest.raises(g.ErrorGeometria, match="rieles"):
        sf.solevar_superficie([a, b], rieles=[seg((10, 0, 0), (10, 0, 30))], condicion_inicio=cond)
    with pytest.raises(g.ErrorGeometria, match="tramos rectos"):
        sf.solevar_superficie([a, b], reglada=True, condicion_inicio=cond)
    with pytest.raises(g.ErrorGeometria, match="no los dos"):
        sf.solevar_superficie([a, b], rieles=[seg((10, 0, 0), (10, 0, 30))], linea_central=seg((0, 0, 0), (0, 0, 30)))


# ================================================================ SUP-13 rieles, línea central y aristas tangentes
def test_un_riel_lleva_al_perfil_y_el_lado_opuesto_queda_recto():
    riel = arco((10, 0, 0), (14, 0, 25), (10, 0, 50))
    f = sf.solevar_superficie([circulo(10), circulo(10, (0, 0, 50))], rieles=[riel])
    assert g.es_valida(f) and toca(f, (14, 0, 25)) and caja(f)[1][0] == pytest.approx(14, abs=0.05)
    assert caja(f)[0][0] == pytest.approx(-10, abs=0.05)         # un riel corre el contorno entero: el lado opuesto llega a -6


def test_dos_rieles_ensanchan_el_contorno():
    a = arco((10, 0, 0), (14, 0, 25), (10, 0, 50))
    b = arco((-10, 0, 0), (-14, 0, 25), (-10, 0, 50))
    f = sf.solevar_superficie([circulo(10), circulo(10, (0, 0, 50))], rieles=[a, b])
    assert g.es_valida(f) and toca(f, (14, 0, 25)) and toca(f, (-14, 0, 25))
    assert g.area(f) > 2 * math.pi * 10 * 50


def test_tres_rieles_en_un_perfil_abierto_pasan_por_los_tres():
    a = arco((0, 0, 0), (0, 5, 25), (0, 0, 50))
    b = arco((5, 0, 0), (5, 8, 25), (5, 0, 50))
    c = arco((10, 0, 0), (10, 3, 25), (10, 0, 50))
    f = sf.solevar_superficie([seg((0, 0, 0), (10, 0, 0)), seg((0, 0, 50), (10, 0, 50))], rieles=[a, b, c])
    assert g.es_valida(f) and all(toca(f, q) for q in ((0, 5, 25), (5, 8, 25), (10, 3, 25)))


def test_un_riel_que_no_toca_o_rieles_cruzados_dicen_por_que():
    with pytest.raises(g.ErrorGeometria, match="no toca"):
        sf.solevar_superficie([circulo(10), circulo(10, (0, 0, 50))], rieles=[seg((30, 0, 0), (30, 0, 50))])
    uno = seg((0, 0, 0), (10, 0, 50))
    otro = seg((10, 0, 0), (0, 0, 50))
    with pytest.raises(g.ErrorGeometria, match="se cruzan"):
        sf.solevar_superficie([seg((0, 0, 0), (10, 0, 0)), seg((0, 0, 50), (10, 0, 50))], rieles=[uno, otro])
    with pytest.raises(g.ErrorGeometria, match="abiertos o todos cerrados"):
        sf.solevar_superficie([circulo(10), seg((10, 0, 50), (0, 0, 50))], rieles=[seg((10, 0, 0), (10, 0, 50))])
    with pytest.raises(g.ErrorGeometria, match="no puntos"):
        sf.solevar_superficie([circulo(10), (0.0, 0.0, 50.0)], rieles=[seg((10, 0, 0), (0, 0, 50))])


def test_riel_por_una_esquina_conserva_las_esquinas():
    riel = arco((10, 10, 0), (14, 14, 25), (10, 10, 50))
    f = sf.solevar_superficie([rectangulo(10), rectangulo(10, 50)], rieles=[riel])
    assert g.es_valida(f) and len(g.caras(f)) == 4 and toca(f, (14, 14, 25))


def test_linea_central():
    f = sf.solevar_superficie([circulo(10), circulo(6, (0, 0, 50))], linea_central=seg((0, 0, 0), (0, 0, 50)))
    assert g.area(f) == pytest.approx(math.pi * 16 * math.hypot(50, 4), rel=2e-3) and g.es_valida(f)


def test_aristas_tangentes_fusionar_junta_las_caras():
    secciones = [rectangulo(10), rectangulo(10, 10), rectangulo(10, 20)]
    mantener = sf.solevar_superficie(secciones, reglada=True)
    fusionar = sf.solevar_superficie(secciones, reglada=True, fusionar_tangentes=True)
    assert len(g.caras(mantener)) == 8 and len(g.caras(fusionar)) == 4
    assert g.area(fusionar) == pytest.approx(g.area(mantener)) and g.es_valida(fusionar)


# ================================================================ SUP-21 bordes de Coser
def _tres_laminas():
    a = sf.extruir_superficie(seg((0, 0, 0), (10, 0, 0)), (0, 0, 1), 10)
    b = sf.extruir_superficie(seg((10, 0, 0), (10, 10, 0)), (0, 0, 1), 10)
    c = sf.extruir_superficie(seg((10.5, 10, 0), (0, 10, 0)), (0, 0, 1), 10)
    return [a, b, c]


def test_bordes_de_costura_cuenta_lista_y_mide_el_hueco():
    r = sf.bordes_de_costura(_tres_laminas(), 0.01)
    assert not r["es_solido"] and r["total_libres"] == 10 and r["aristas_cosidas"] == 1 and len(r["cosidas"]) == 1
    bordes = {tuple(b["punto"]): b for b in r["libres"]}
    assert bordes[(10.0, 10.0, 5.0)]["hueco"] == pytest.approx(0.5, abs=1e-6)
    assert bordes[(10.5, 10.0, 5.0)]["hueco"] == pytest.approx(0.5, abs=1e-6)
    assert bordes[(10.0, 10.0, 5.0)]["largo"] == pytest.approx(10)
    assert r["libres"][0]["polilinea"].shape == (25, 3)
    arreglado = sf.bordes_de_costura(_tres_laminas(), 0.6)
    assert arreglado["aristas_cosidas"] == 2 and arreglado["total_libres"] == 8


def test_bordes_de_costura_de_una_caja_cierra_y_no_toca_el_documento():
    caras = sf.descoser(g.caja(10, 10, 10))
    antes = [g.caja_envolvente(c) for c in caras]
    r = sf.bordes_de_costura(caras, 0.01)
    assert r["es_solido"] and r["libres"] == [] and r["aristas_cosidas"] == 12
    assert [g.caja_envolvente(c) for c in caras] == antes
    with pytest.raises(g.ErrorGeometria, match="tolerancia"):
        sf.bordes_de_costura(caras, 0.0)


def test_borde_suelto_no_tiene_hueco_y_la_tabla_tiene_tope():
    r = sf.bordes_de_costura([g.caras(g.caja(10, 10, 10))[0]], 0.01)
    assert r["total_libres"] == 4 and r["libres"][0]["hueco"] == pytest.approx(10)
    sola = sf.bordes_de_costura([sf.extruir_superficie(circulo(5), (0, 0, 1), 10)], 0.01)
    assert sola["total_libres"] == 2
    muchas = [sf.extruir_superficie(seg((i * 2, 0, 0), (i * 2 + 1, 0, 0)), (0, 0, 1), 1) for i in range(60)]
    r = sf.bordes_de_costura(muchas, 0.01)
    assert r["total_libres"] == 240 and len(r["libres"]) == sf.BORDES_MAXIMOS


class _Visor:
    def __init__(self):
        self.encuadres = []

    def encuadrar(self, puntos):
        self.encuadres.append(np.asarray(puntos))


class _Panel:
    def __init__(self):
        self.visor, self.ultima_op, self.previas = _Visor(), None, 0

    def _previa_vista(self, _op):
        self.previas += 1


def test_tabla_de_coser_recorre_los_bordes_y_la_vista_marca_en_verde_y_rojo():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.superficie import Coser
    doc = Documento()
    bid, ids = _boceto(doc, lineas=[((0, 0), (10, 0)), ((10, 0), (10, 10))])
    from omnicad.ui.comandos.superficie import SupExtruir
    for i in ids:
        _ejecutar(doc, SupExtruir, curvas=_curvas(doc, bid, [i]), distancia="5 mm")
    cuerpos = [_hit_cuerpo(doc, c) for c in doc.estado_final.cuerpos]
    cmd, ctx, panel = Coser(), ContextoComando(doc), _Panel()
    t = cmd._tabla(panel)
    v = {"cuerpos": cuerpos, "tolerancia": "0.01 mm"}
    assert cmd._libres(v, ctx) == "6 bordes libres · 1 arista se cose: el resultado sigue siendo una superficie."
    assert t.rowCount() == 6 and t.item(0, 0).text() == "1" and t.item(0, 1).text().endswith(" mm")
    previa = cmd.previa_vista(ctx, v, None)
    assert [p[2] for p in previa] == [Coser.VERDE, Coser.ROJO] and previa[0][0] == "lineas"
    t.setCurrentCell(2, 0)
    assert panel.previas == 1 and len(panel.visor.encuadres) == 1
    assert len(cmd.previa_vista(ctx, v, None)) == 3 and cmd.previa_vista(ctx, v, None)[-1][2] == Coser.ELEGIDO
    assert len(cmd.previa_vista(ctx, v, None)[1][1]) < len(previa[1][1])       # el elegido sale de los rojos
    assert cmd._libres({"cuerpos": [], "tolerancia": "0.01 mm"}, ctx) == "Elegí las superficies." and t.rowCount() == 0
    assert cmd.previa_vista(ctx, v, None) is None


# ================================================================ pasos y diálogos
def _sketch_con(doc, plano, lineas):
    bid, ids = _boceto(doc, plano=plano, lineas=lineas)
    return _curvas(doc, bid, ids)


def test_paso_de_barrido_con_riel_conicidad_y_reabrir():
    from omnicad.ui.comandos.superficie import SupBarrido
    doc = Documento()
    perfil = _sketch_con(doc, "XY", [((0, 0), (10, 0))])
    ruta = _sketch_con(doc, "XZ", [((0, 0), (0, 100))])
    riel = _sketch_con(doc, "XZ", [((10, 0), (20, 100))])
    op, _ = _ejecutar(doc, SupBarrido, tipo="ruta_carril", perfil=perfil, ruta=ruta, carril=riel)
    forma = _ultimo(doc).forma
    assert g.area(forma) == pytest.approx(1500, rel=1e-6) and _ultimo(doc).tipo == "superficie"
    assert op.p["escala_carril"] == "escalar" and op.p["cadena"] is True
    _roundtrip(SupBarrido, op, doc)
    op2, _ = _ejecutar(doc, SupBarrido, perfil=perfil, ruta=ruta, conicidad="5 deg", cadena=False)
    assert g.area(_ultimo(doc).forma) == pytest.approx(1437.44, rel=1e-4) and op2.p["carril"] == []
    _roundtrip(SupBarrido, op2, doc)
    with pytest.raises(Exception, match="rail"):
        _ejecutar(doc, SupBarrido, tipo="ruta_carril", perfil=perfil, ruta=ruta)


def test_seleccion_de_cadena_suma_las_curvas_tangentes_de_la_ruta():
    from omnicad.ui.comandos.superficie import SupBarrido
    doc = Documento()
    perfil = _sketch_con(doc, "XZ", [((-1, 0), (1, 0))])
    ruta = _sketch_con(doc, "XY", [((0, 0), (0, 10)), ((0, 10), (0, 20))])
    _ejecutar(doc, SupBarrido, perfil=perfil, ruta=ruta[:1], cadena=False)
    assert g.area(_ultimo(doc).forma) == pytest.approx(20)
    _ejecutar(doc, SupBarrido, perfil=perfil, ruta=ruta[:1], cadena=True)
    assert g.area(_ultimo(doc).forma) == pytest.approx(40)


def test_paso_de_solevacion_saca_la_cara_del_perfil_y_reabre():
    from omnicad.ui.comandos.superficie import SupExtruir, SupSolevacion
    doc = Documento()
    _ejecutar(doc, SupExtruir, curvas=_sketch_con(doc, "XY", [((0, 0), (10, 0))]), distancia="10 mm")
    lamina = _ultimo(doc)
    from omnicad.nucleo import referencias as refs
    borde = next(e for e in refs.subformas(lamina.forma, "arista") if caja(e)[0][2] == pytest.approx(10) and caja(e)[1][2] == pytest.approx(10))
    from test_superficie_fusion import _h
    hit = _h(doc, refs.referencia(lamina.id, borde, lamina.forma))
    lejos = _sketch_con(doc, "XY", [((0, 15), (10, 15))])
    op, _ = _ejecutar(doc, SupSolevacion, secciones=[hit, *lejos], condicion_inicio="tangente", peso_inicio="1.5",
                      alineacion_inicio="alinear", cadena=False)
    assert op.p["condicion_inicio"] == {"tipo": "tangente", "angulo": "90 deg", "peso": "1.5", "cara": None, "alineacion": "alinear"}
    assert "operacion" not in op.p and g.es_valida(_ultimo(doc).forma)
    assert _ultimo(doc).tipo == "superficie" and caja(_ultimo(doc).forma)[1][2] > 10.5
    _roundtrip(SupSolevacion, op, doc)
    op2, _ = _ejecutar(doc, SupSolevacion, secciones=[*lejos, hit], aristas_tangentes="fusionar", cadena=False)
    assert op2.p["fusionar_tangentes"] is True and op2.p["condicion_fin"] is None


def test_paso_de_solevacion_con_rieles_y_punto_tangente():
    from omnicad.restricciones import Boceto
    from omnicad.ui.comandos.superficie import SupSolevacion
    from test_superficie_fusion import _h
    doc = Documento()
    secciones = _sketch_con(doc, "XZ", [((0, 0), (10, 0)), ((0, 50), (10, 50))])
    rieles = _sketch_con(doc, "XZ", [((0, 0), (0, 50)), ((10, 0), (10, 50))])
    op, _ = _ejecutar(doc, SupSolevacion, secciones=secciones, carriles=rieles, cadena=False)
    assert len(op.p["carriles"]) == 2 and g.area(_ultimo(doc).forma) == pytest.approx(500, rel=1e-3)
    _roundtrip(SupSolevacion, op, doc)
    op, _ = _ejecutar(doc, SupSolevacion, secciones=secciones, guia="linea_central",
                      linea_central=_sketch_con(doc, "YZ", [((0, 0), (0, 50))]), cadena=False)
    assert op.p["linea_central"] and g.es_valida(_ultimo(doc).forma)
    _roundtrip(SupSolevacion, op, doc)
    circ, sub = Boceto(), Boceto()
    c, q = circ.agregar_circulo((0, 0), 10), sub.agregar_punto(0, 10)
    pid, sid = doc.nuevo_id(), None
    doc.agregar(OpBoceto(pid, plano="XY", boceto=circ))
    sid = doc.nuevo_id()
    doc.agregar(OpBoceto(sid, plano="XZ", boceto=sub))
    punta = _h(doc, {"tipo": "punto_boceto", "boceto": sid, "punto": q})
    seccion = _h(doc, {"tipo": "curva_boceto", "boceto": pid, "curva": c})
    op, _ = _ejecutar(doc, SupSolevacion, secciones=[seccion, punta], condicion_fin="punto_tangente", cadena=False)
    assert op.p["condicion_fin"]["tipo"] == "punto_tangente"
    assert g.area(_ultimo(doc).forma) == pytest.approx(628.3, rel=3e-3)
    _roundtrip(SupSolevacion, op, doc)


def test_coser_con_tolerancia_invalida_no_rompe_el_panel():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.superficie import Coser, SupExtruir
    doc = Documento()
    bid, ids = _boceto(doc, lineas=[((0, 0), (10, 0))])
    _ejecutar(doc, SupExtruir, curvas=_curvas(doc, bid, ids), distancia="5 mm")
    cuerpos = [_hit_cuerpo(doc, c) for c in doc.estado_final.cuerpos]
    cmd, ctx = Coser(), ContextoComando(doc)
    cmd._tabla(_Panel())
    v = {"cuerpos": cuerpos, "tolerancia": "0 mm"}
    assert cmd._libres(v, ctx) == "" and cmd._libres(v, ctx) == ""          # el panel lo vuelve a pedir: sin TypeError
    assert cmd._libres(dict(v, tolerancia="0.01 mm"), ctx).startswith("4 bordes libres")
    assert cmd._libres(v, ctx) == "" and cmd.previa_vista(ctx, v, None) is None   # nada viejo en la vista


def test_barrido_no_manda_valores_de_campos_ocultos():
    from omnicad.ui.comandos.superficie import SupBarrido
    doc = Documento()
    perfil = _sketch_con(doc, "XY", [((0, 0), (10, 0))])
    ruta = _sketch_con(doc, "XZ", [((0, 0), (0, 20))])
    op, _ = _ejecutar(doc, SupBarrido, perfil=perfil, ruta=ruta, orientacion="paralela", conicidad="5 deg", torsion="30 deg",
                      distancia_carril="2", cadena=False)
    assert (op.p["conicidad"], op.p["torsion"], op.p["distancia_carril"]) == ("0 deg", "0 deg", "1")
    assert g.area(_ultimo(doc).forma) == pytest.approx(200)


def test_fila_de_la_solevacion_descarta_la_condicion_del_perfil_que_ya_no_esta():
    from types import SimpleNamespace

    from omnicad.ui.comandos.superficie import SupSolevacion
    curva, punto = {"ref": {"tipo": "curva_boceto"}}, {"ref": {"tipo": "punto_boceto"}}
    panel = SimpleNamespace(valores={"secciones": [curva, punto], "condicion_inicio": "punto_tangente"})
    assert SupSolevacion()._celda(panel, 0, 2).currentData() == "libre" and panel.valores["condicion_inicio"] == "libre"
    panel = SimpleNamespace(valores={"secciones": [punto, curva], "condicion_inicio": "tangente"})
    assert SupSolevacion()._celda(panel, 0, 2).currentData() == "libre" and panel.valores["condicion_inicio"] == "libre"
    panel = SimpleNamespace(valores={"secciones": [punto, curva], "condicion_inicio": "punto_tangente"})
    assert SupSolevacion()._celda(panel, 0, 2).currentData() == "punto_tangente"


def test_riel_de_dos_curvas_con_seleccion_de_cadena():
    from omnicad.ui.comandos.superficie import SupSolevacion
    doc = Documento()
    secciones = _sketch_con(doc, "XZ", [((0, 0), (10, 0)), ((0, 50), (10, 50))])
    a = _sketch_con(doc, "XZ", [((0, 0), (0, 20)), ((0, 20), (0, 50))])
    b = _sketch_con(doc, "XZ", [((10, 0), (10, 30)), ((10, 30), (10, 50))])
    _ejecutar(doc, SupSolevacion, secciones=secciones, carriles=a + b[:1], cadena=True)     # dos tramos del riel a: uno solo
    assert g.area(_ultimo(doc).forma) == pytest.approx(500, rel=1e-3)


def test_receta_vieja_de_barrido_y_solevacion_se_abre_igual():
    viejos = OpSupBarrido.PARAMS
    assert (viejos["perfil"], viejos["ruta"], viejos["orientacion"], viejos["torsion"], viejos["distancia"]) == ([], [], "perpendicular", "0 deg", "1")
    assert OpSupSolevacion.PARAMS["cerrada"] is False and OpSupSolevacion.PARAMS["reglada"] is False
    doc = Documento()
    perfil = _sketch_con(doc, "XY", [((0, 0), (10, 0))])
    ruta = _sketch_con(doc, "XZ", [((0, 0), (0, 20))])
    op = OpSupBarrido(doc.nuevo_id(), perfil=[h["ref"] for h in perfil], ruta=[h["ref"] for h in ruta])
    assert doc.agregar(op).estado == "ok" and g.area(_ultimo(doc).forma) == pytest.approx(200)
    assert op.p["cadena"] is False and op.p["carril"] == []


AREAS = {"sup_caja": ({"ancho": "10 mm", "largo": "20 mm", "alto": "30 mm"}, 2 * (200 + 300 + 600)),
         "sup_cilindro": ({"diametro": "20 mm", "alto": "30 mm"}, 2 * math.pi * 10 * (10 + 30)),
         "sup_esfera": ({"diametro": "20 mm"}, 4 * math.pi * 100),
         "sup_toroide": ({"diametro": "40 mm", "diametro_tubo": "10 mm"}, 4 * math.pi ** 2 * 20 * 5)}


@pytest.mark.parametrize("clave", AREAS)
def test_primitivas_de_superficie_dan_una_superficie_con_el_area_del_solido(clave):
    from omnicad.ui.comandos import CATALOGO, comando_para
    doc = Documento()
    op, _ = _ejecutar(doc, CATALOGO[clave], **AREAS[clave][0])
    c = _ultimo(doc)
    assert c.tipo == "superficie" and g.area(c.forma) == pytest.approx(AREAS[clave][1], rel=1e-3) and g.es_valida(c.forma)
    assert not g.solidos(c.forma) and comando_para(op) is CATALOGO[clave] and op.TIPO == OpSupPrimitiva.TIPO
    _roundtrip(CATALOGO[clave], op, doc)


def test_bobina_y_tuberia_de_superficie():
    from omnicad.ui.comandos import CATALOGO, comando_para
    doc = Documento()
    op, _ = _ejecutar(doc, CATALOGO["sup_bobina"], diametro="20 mm", tamano="2 mm", revoluciones="3", altura="20 mm")
    c = _ultimo(doc)
    largo = 3 * math.hypot(2 * math.pi * 10, 20 / 3)
    assert c.tipo == "superficie" and g.area(c.forma) == pytest.approx(math.pi * 2 * largo, rel=0.02) and g.es_valida(c.forma)
    assert comando_para(op) is CATALOGO["sup_bobina"] and caja(c.forma)[1][2] > 19
    _roundtrip(CATALOGO["sup_bobina"], op, doc)
    ruta = _sketch_con(doc, "XZ", [((50, 0), (50, 40))])
    op, _ = _ejecutar(doc, CATALOGO["sup_tuberia"], ruta=ruta, tamano="10 mm")
    c = _ultimo(doc)
    assert c.tipo == "superficie" and g.es_valida(c.forma)
    assert g.area(c.forma) == pytest.approx(2 * math.pi * 5 * 45, rel=1e-3)
    _roundtrip(CATALOGO["sup_tuberia"], op, doc)


def test_el_panel_de_las_primitivas_no_pide_operacion():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos import CATALOGO
    ctx = ContextoComando(Documento())
    for clave in ("sup_caja", "sup_bobina", "sup_tuberia", "sup_solevacion"):
        campos = {c.clave: c for c in CATALOGO[clave]().campos(ctx)}
        assert not campos["operacion"].visible_si({"operacion": "unir"}), clave


def test_cinta_tiene_las_seis_primitivas():
    from omnicad.ui import cinta
    crear = next(g_ for g_ in cinta.SUPERFICIE if g_[0] == "CREAR")[2]
    claves = [i[2] for i in crear if i[0] == "item"]
    assert {"sup_caja", "sup_cilindro", "sup_esfera", "sup_toroide", "sup_bobina", "sup_tuberia"} <= set(claves)


# ================================================================ API (MCP y CLI)
def _sesion():
    return api.Sesion()


def test_api_primitivas():
    s = _sesion()
    formas = []
    formas.append(llamar(s, "create_surface_box", length=10, width=20, height=30))
    formas.append(llamar(s, "create_surface_cylinder", diameter=20, height=30, x=50))
    formas.append(llamar(s, "create_surface_sphere", radius=10, x=100))
    formas.append(llamar(s, "create_surface_torus", major_radius=20, minor_radius=5, x=150, position="outside"))
    formas.append(llamar(s, "create_surface_coil", diameter=20, section_size=2, revolutions=3, height=20, center_point=[200, 0, 0]))
    areas = [2200, 2 * math.pi * 10 * 40, 400 * math.pi, 4 * math.pi ** 2 * 25 * 5, None]
    for r, area in zip(formas, areas, strict=True):
        c = s.cuerpo(r["bodies_created"][0]["id"])
        assert c.tipo == "superficie" and g.es_valida(c.forma)
        if area is not None:
            assert g.area(c.forma) == pytest.approx(area, rel=1e-3)
    ruta = _linea(s, "Ruta", "XZ", (300, 0), (300, 40))
    r = llamar(s, "create_surface_pipe", path=ruta, section="square", section_size=10)
    assert s.cuerpo(r["bodies_created"][0]["id"]).tipo == "superficie"
    assert falla(s, "create_surface_box", length=-1, width=1, height=1)["error_kind"] == "INVALID_ARGUMENTS"
    assert falla(s, "create_surface_cylinder", height=1, radius=1, diameter=1)["error_kind"] == "INVALID_ARGUMENTS"


def test_api_barrido_con_riel_estirar_superficie_guia_y_conicidad():
    s = _sesion()
    perfil, ruta = _linea(s), _linea(s, "Ruta", "XZ", (0, 0), (0, 100))
    riel = _linea(s, "Riel", "XZ", (10, 0), (20, 100))
    r = llamar(s, "create_surface_sweep", profiles=perfil, path=ruta, guide_rail=riel)
    assert g.area(s.cuerpo(r["bodies_created"][0]["id"]).forma) == pytest.approx(1500, rel=1e-6)
    r = llamar(s, "create_surface_sweep", profiles=perfil, path=ruta, guide_rail=riel, profile_scaling="none")
    assert g.area(s.cuerpo(r["bodies_created"][0]["id"]).forma) == pytest.approx(1000, rel=1e-6)
    r = llamar(s, "create_surface_sweep", profiles=perfil, path=ruta, guide_rail=riel, extent="full_extents", path_distance=0.5,
               rail_distance=0.5)
    assert g.area(s.cuerpo(r["bodies_created"][0]["id"]).forma) == pytest.approx(625, rel=1e-6)
    r = llamar(s, "create_surface_sweep", profiles=perfil, path=ruta, taper_angle=5)
    assert g.area(s.cuerpo(r["bodies_created"][0]["id"]).forma) == pytest.approx(1437.44, rel=1e-4)
    c = llamar(s, "create_surface_cylinder", radius=20, height=100, x=0, y=0, z=0)
    assert falla(s, "create_surface_sweep", profiles=perfil, path=ruta, guide_rail=riel, guide_surface=c["bodies_created"][0]["id"])
    assert falla(s, "create_surface_sweep", profiles=perfil, path=ruta, taper_angle=5, orientation="parallel")


def test_api_solevacion_con_condiciones_y_rieles():
    s = _sesion()
    abajo = _linea(s, "Abajo", "XZ", (0, 0), (10, 0))
    arriba = _linea(s, "Arriba", "XZ", (0, 50), (10, 50))
    riel = _linea(s, "Riel1", "XZ", (0, 0), (0, 50))
    riel2 = _linea(s, "Riel2", "XZ", (10, 0), (10, 50))
    r = llamar(s, "create_surface_loft", profiles=[abajo, arriba], rails=[riel, riel2])
    assert g.area(s.cuerpo(r["bodies_created"][0]["id"]).forma) == pytest.approx(500, rel=1e-3)
    r = llamar(s, "create_surface_loft", profiles=[abajo, arriba], start_condition={"type": "direction", "angle": 45, "weight": 2})
    assert g.es_valida(s.cuerpo(r["bodies_created"][0]["id"]).forma)
    op = s.doc.operaciones[-1]
    assert op.p["condicion_inicio"]["tipo"] == "direccion" and float(op.p["condicion_inicio"]["peso"]) == 2
    r = llamar(s, "create_surface_loft", profiles=[abajo, arriba], center_line=[_linea(s, "Centro", "YZ", (0, 0), (0, 50))])
    assert s.cuerpo(r["bodies_created"][0]["id"]).tipo == "superficie"
    assert falla(s, "create_surface_loft", profiles=[abajo, arriba], rails=[riel], center_line=[riel2])
    assert falla(s, "create_surface_loft", profiles=[abajo, arriba], start_condition={"type": "xx"})
    assert falla(s, "create_surface_loft", profiles=[abajo, arriba], start_condition={"type": "direction", "angle": 200})
    assert falla(s, "create_surface_loft", profiles=[abajo, arriba], start_condition={"type": "direction", "weight": 0})
    assert falla(s, "create_surface_loft", profiles=[abajo, arriba], section_conditions={"1": {"type": "direction"}})


def test_api_solevacion_tangente_contra_un_cuerpo_y_punto_tangente():
    s = _sesion()
    base = _linea(s)
    lamina = llamar(s, "create_surface_extrude", profiles=base, distance=10)["bodies_created"][0]["id"]
    arista = {"body": lamina, "edges": ">Z"}
    lejos = _linea(s, "Lejos", "XY", (0, 30), (10, 30))
    r = llamar(s, "create_surface_loft", profiles=[arista, lejos],
               start_condition={"type": "tangent", "edge_alignment": "align", "weight": 1.5})
    f = s.cuerpo(r["bodies_created"][0]["id"]).forma
    assert g.es_valida(f) and caja(f)[1][2] > 10.5
    assert s.doc.operaciones[-1].p["condicion_inicio"]["alineacion"] == "alinear"


def test_api_inspeccionar_costura_no_cambia_el_documento():
    s = _sesion()
    uno = llamar(s, "create_surface_extrude", profiles=_linea(s), distance=5)["bodies_created"][0]["id"]
    otro = llamar(s, "create_surface_extrude", profiles=_linea(s, "B", "XY", (10.2, 0), (20, 0)), distance=5)["bodies_created"][0]["id"]
    pasos = len(s.doc.operaciones)
    r = llamar(s, "inspect_stitch", bodies=[uno, otro], tolerance=0.01)
    assert not r["closes_solid"] and r["free_edge_count"] == 8 and r["stitched_edges"] == 0
    assert min(b["gap"] for b in r["free_edges"]) == pytest.approx(0.2, abs=1e-6) and len(s.doc.operaciones) == pasos
    r = llamar(s, "inspect_stitch", bodies=[uno, otro], tolerance=0.5)
    assert r["stitched_edges"] == 1 and r["free_edge_count"] == 6
    assert falla(s, "inspect_stitch", bodies=[uno], tolerance=0)


# ================================================================ B-114, B-115, alias y cadena única
def test_b114_solevacion_con_tangente_en_la_boca_de_una_extrusion():
    from omnicad.nucleo import solidos_crear as sc
    tubo = sf.extruir_superficie(circulo(10), (0, 0, 1), 20)
    boca = next(e for e in aristas(tubo) if caja(e)[0][2] == pytest.approx(20))
    cae = sc.solevar([boca, circulo(5, (0, 0, 30))], condicion_inicio={"tipo": "tangente", "cara": g.caras(tubo)[0]}, solido=False)
    assert g.es_valida(cae) and abs(tangente_de_salida(cae)[2]) > 0.97


def test_b115_arco_de_torsion_solo_si_se_ve_el_campo():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Barrido
    from omnicad.ui.comandos.superficie import SupBarrido
    doc = Documento()
    ruta = _sketch_con(doc, "XZ", [((0, 0), (0, 20))])
    ctx = ContextoComando(doc)

    def tiene_arco(cmd, tipo, orientacion="perpendicular"):
        return "torsion" in [m.clave for m in cmd.manipuladores(ctx, {"ruta": ruta, "tipo": tipo, "orientacion": orientacion})]

    assert tiene_arco(SupBarrido(), "ruta") and not tiene_arco(SupBarrido(), "ruta", "paralela")
    assert not tiene_arco(SupBarrido(), "ruta_carril") and not tiene_arco(SupBarrido(), "ruta_superficie")
    assert tiene_arco(Barrido(), "ruta_carril") and not tiene_arco(Barrido(), "cuerpo")     # en sólido el campo sigue ahí


def test_edit_feature_acepta_los_nombres_de_la_herramienta_en_primitivas_de_superficie():
    s = api.Sesion()
    r = api.llamar(s, "create_surface_box", {"length": 10, "width": 20, "height": 30})
    assert r["ok"], r
    paso = api.llamar(s, "get_timeline")["result"]["steps"][-1]
    assert paso["aliases"] == {"length": "ancho", "width": "largo", "height": "alto"}
    r = api.llamar(s, "edit_feature", {"feature": paso["id"], "params": {"length": 40}})
    assert r["ok"], r
    (x0, _, _), (x1, _, _) = caja(next(iter(s.doc.estado_final.cuerpos.values())).forma)
    assert x1 - x0 == pytest.approx(40)


def test_tramos_de_un_mismo_riel_cuentan_una_vez_y_la_ruta_no_se_repite(monkeypatch):
    from omnicad.ui.comandos.superficie import SupBarrido, SupSolevacion
    doc = Documento()
    secciones = _sketch_con(doc, "XZ", [((0, 0), (10, 0)), ((0, 50), (10, 50))])
    a = _sketch_con(doc, "XZ", [((0, 0), (0, 20)), ((0, 20), (0, 50))])
    b = _sketch_con(doc, "XZ", [((10, 0), (10, 50))])
    vistos, original = [], sf.solevar_superficie
    monkeypatch.setattr(sf, "solevar_superficie", lambda *x, **k: vistos.append(k["rieles"]) or original(*x, **k))
    _ejecutar(doc, SupSolevacion, secciones=secciones, carriles=a + b, cadena=True)
    assert [len(r) for r in vistos[-1]] == [2, 1]
    perfil = _sketch_con(doc, "XY", [((-1, 0), (1, 0))])
    ruta = _sketch_con(doc, "XZ", [((0, 0), (0, 10)), ((0, 10), (0, 20))])
    _ejecutar(doc, SupBarrido, perfil=perfil, ruta=ruta, cadena=True)      # las dos curvas de una cadena: sin aristas repetidas
    assert g.area(_ultimo(doc).forma) == pytest.approx(40)


def test_tuberia_con_cadena_sobre_una_curva_de_construccion():
    from omnicad.restricciones import Boceto
    from omnicad.timeline.ops_solido import OpTuberia
    from test_superficie_fusion import _h
    doc = Documento()
    b = Boceto()
    linea = b.agregar_linea((0, 0), (0, 20), construccion=True)
    bid = doc.nuevo_id()
    doc.agregar(OpBoceto(bid, plano="XZ", boceto=b))
    ref = _h(doc, {"tipo": "curva_boceto", "boceto": bid, "curva": linea})["ref"]
    op = OpTuberia(doc.nuevo_id(), ruta=[ref], cadena=True, tamano="4 mm")
    res = doc.agregar(op)
    assert res.estado == "ok", res.mensaje
    assert caja(_ultimo(doc).forma)[1][2] == pytest.approx(20, abs=0.01)
