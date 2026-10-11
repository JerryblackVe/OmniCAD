# -*- coding: utf-8 -*-
"""Herramientas de la pestaña BOCETO (CREAR, MODIFICAR, RESTRICCIONES) con el Lienzo 2D y el modelo."""
import math

import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo.perfiles import detectar, intersecar_forma, proyectar_forma
from omnicad.restricciones import Boceto, ErrorBoceto, auto_restringir, grados_de_libertad, puntos_primitiva, resolver
from omnicad.restricciones.boceto import (distancia_primitiva, distancia_punto_recta, dominio, evaluar_primitiva,
                                              mas_cercano, validar_valor_cota)
from omnicad.timeline.parametros import TablaParametros

PLANO = g.Plano("XY")


@pytest.fixture(scope="module")
def app_qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _lienzo(app_qt, boceto=None):
    from omnicad.ui.editor_boceto import Lienzo
    lz = Lienzo(boceto or Boceto(), TablaParametros().evaluar, plano=PLANO)
    lz.ajustar_grilla = False
    return lz


def _crear(lz, herramienta, *puntos):
    lz.set_herramienta(herramienta)
    for p in puntos:
        lz.clics.append((None, p))
        lz._procesar_clics()


def _aceptar(lz, *valores):
    assert lz.entrada is not None
    lz.entrada.aceptado.emit(list(valores))


def _tipos(b):
    return sorted(c.tipo for c in b.curvas.values())


def _valores(b):
    return {k.id: float(k.expresion) for k in b.cotas.values()}


def _areas(b):
    return sorted(round(p.area, 6) for p in detectar(b.geometria(), PLANO))


# ---------------------------------------------------------------- puntos_primitiva (la usa el visor 3D)
def test_puntos_primitiva_muestrea_todos_los_tipos():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    b.agregar_circulo((0, 0), 5)
    b.agregar_arco_3_puntos((10, 0), (14, 4), (18, 0))
    e = b.agregar_elipse((30, 0), (40, 0), 4)
    b.agregar_spline([(0, 20), (10, 25), (20, 20)])
    b.agregar_conica((0, 40), (10, 50), (20, 40), 0.3)
    b.agregar_texto((0, 60), "A", 8)
    b.agregar_linea((15, 0), (45, 0))
    b.recortar(e, (32, 3.9))
    tipos = set()
    for prim in b.geometria(incluir_construccion=True):
        pts = puntos_primitiva(prim, 32)
        tipos.add(prim[0])
        assert len(pts) >= 2 and all(len(q) == 2 for q in pts)
        assert all(distancia_primitiva(prim, q) < 1e-6 for q in pts)
        if prim[0] == "circulo":
            assert pts[0] == pytest.approx(pts[-1])
    assert tipos == {"linea", "circulo", "arco", "arco_elipse", "spline"}
    assert puntos_primitiva(("elipse", 1, (0, 0), 3, 2, 0.0), 16)[4] == pytest.approx((0, 2))


# ---------------------------------------------------------------- CREAR
def test_elipse_con_ejes_y_perfil_de_area_pi_a_b(app_qt):
    lz = _lienzo(app_qt)
    _crear(lz, "elipse", (20, 10), (30, 10), (23, 14))                  # lejos del origen (que fija el centro)
    assert _tipos(lz.b) == ["elipse", "linea", "linea"]                # + ejes mayor y menor de construcción
    assert all(c.construccion for c in lz.b.curvas.values() if c.tipo == "linea")
    assert lz.resultado.ok and lz.resultado.gdl == 5
    assert _areas(lz.b) == [pytest.approx(math.pi * 10 * 4)]


@pytest.mark.parametrize("herramienta, puntos, area", [
    ("ranura_centro", [(0, 0), (20, 0), (10, 3)], 20 * 6 + math.pi * 9),
    ("ranura_total", [(0, 0), (26, 0), (10, 3)], 20 * 6 + math.pi * 9),
    ("ranura_punto", [(10, 0), (20, 0), (10, 3)], 20 * 6 + math.pi * 9),
    ("ranura_arco_3p", [(-10, 0), (10, 0), (0, 10), (0, 12)], 10 * math.pi * 4 + math.pi * 4),   # media vuelta
    ("ranura_arco_centro", [(0, 0), (10, 0), (0, 10), (0, 12)], 5 * math.pi * 4 + math.pi * 4),  # un cuarto
])
def test_ranuras(app_qt, herramienta, puntos, area):
    lz = _lienzo(app_qt)
    _crear(lz, herramienta, *puntos)
    tipos = _tipos(lz.b)
    assert tipos.count("arco") >= 2 and lz.resultado.ok
    assert sum(r.tipo == "tangente" for r in lz.b.restricciones.values()) == 4
    assert _areas(lz.b) == [pytest.approx(area, rel=1e-6)]


def test_spline_de_ajuste_pasa_por_sus_puntos_y_cerrada_da_perfil(app_qt):
    lz = _lienzo(app_qt)
    pts = [(0, 0), (10, 6), (20, -3), (30, 4)]
    _crear(lz, "spline_ajuste", *pts)
    sid = lz._terminar_spline()
    prim = lz.b.primitivas(sid)[0]
    assert all(distancia_primitiva(prim, q) < 1e-9 for q in pts)
    assert len(lz.b.curvas[sid].pts) == 4 and lz.resultado.ok
    lz.set_herramienta("spline_ajuste")
    for q in [(50, 0), (60, 10), (70, 0), (60, -8), (50, 0)]:     # el último clic en el primero la cierra
        lz.clics.append((None, q))
        lz._procesar_clics()
    cerrada = max(lz.b.curvas)
    assert lz.b.curvas[cerrada].cerrada and len(detectar(lz.b.geometria(), PLANO)) == 1


def test_spline_de_control_y_su_grado(app_qt):
    lz = _lienzo(app_qt)
    lz.opciones["grado_spline"] = 5
    _crear(lz, "spline_control", *[(i * 10.0, (-1) ** i * 5.0) for i in range(7)])
    sid = lz._terminar_spline()
    prim = lz.b.primitivas(sid)[0]
    assert prim[4] == 5 and evaluar_primitiva(prim, 0)[0] == pytest.approx((0, 5))   # sujeta en los extremos
    assert lz.resultado.ok and lz.resultado.gdl == 14


def test_conica_rho_05_es_una_parabola(app_qt):
    lz = _lienzo(app_qt)
    _crear(lz, "conica", (0, 0), (20, 0), (10, 10))
    _aceptar(lz, "0.5")
    _crear(lz, "linea", (0, 0), (20, 0))
    assert lz.resultado.ok and _areas(lz.b) == [pytest.approx(2 / 3 * 20 * 5)]   # área de un segmento parabólico


def test_texto_da_perfiles_y_desglosar_lo_vuelve_curvas_fijas(app_qt):
    lz = _lienzo(app_qt)
    _crear(lz, "texto", (0, 0), (0, 0))               # dos clics en el mismo lugar: texto suelto sin cuadro
    _aceptar(lz, "Hola", "10", "0")
    tid = next(iter(lz.b.curvas))
    assert lz.b.tipo_de(tid) == "texto" and len(detectar(lz.b.geometria(), PLANO)) >= 4
    lz.set_herramienta("desglosar_texto")
    lz.agregar_pick(tid, (0, 0))
    assert "texto" not in _tipos(lz.b) and {"linea", "spline"} <= set(_tipos(lz.b))
    assert any(r.tipo == "fijo" for r in lz.b.restricciones.values()) and lz.resultado.ok
    assert len(detectar(lz.b.geometria(), PLANO)) >= 4


def test_circulo_de_2_y_3_tangentes(app_qt):
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (20, 0))
    l2 = lz.b.agregar_linea((0, 0), (0, 20))
    lz.set_herramienta("circulo_2t")
    lz.agregar_pick(l1, (10, 0))
    lz.agregar_pick(l2, (0, 10))
    lz.clics.append((None, (4, 4)))
    lz._procesar_clics()
    c = next(k for k in lz.b.curvas.values() if k.tipo == "circulo")
    centro = lz.b.coords(c.centro)
    assert centro == pytest.approx((c.radio, c.radio)) and lz.resultado.ok
    lz = _lienzo(app_qt)
    ls = [lz.b.agregar_linea(a, b) for a, b in (((0, 0), (12, 0)), ((12, 0), (0, 9)), ((0, 9), (0, 0)))]
    lz.set_herramienta("circulo_3t")
    for k, xy in zip(ls, [(6, 0), (6, 4.5), (0, 4.5)], strict=True):
        lz.agregar_pick(k, xy)
    c = next(k for k in lz.b.curvas.values() if k.tipo == "circulo")
    assert c.radio == pytest.approx((12 + 9 - 15) / 2)                   # inscrito del triángulo 9-12-15
    assert sum(r.tipo == "tangente" for r in lz.b.restricciones.values()) == 3 and lz.resultado.ok


def test_simetria_patrones_y_espiral(app_qt):
    lz = _lienzo(app_qt)
    eje = lz.b.agregar_linea((0, -10), (0, 10), True)
    ln = lz.b.agregar_linea((2, 0), (8, 3))
    lz.seleccion = [ln]
    lz.set_herramienta("simetria")
    assert lz.fase == "eje"
    lz.agregar_pick(eje, (0, 0))
    otra = max(k for k, c in lz.b.curvas.items() if c.tipo == "linea")
    assert sorted(lz.b._extremos_linea(otra)) == [pytest.approx((-8, 3)), pytest.approx((-2, 0))]
    assert lz.resultado.ok
    lz = _lienzo(app_qt)
    c = lz.b.agregar_circulo((0, 0), 2)
    lz.seleccion = [c]
    lz.set_herramienta("patron_rectangular")
    _aceptar(lz, "3", "20", "2", "10")
    centros = sorted(lz.b.coords(k.centro) for k in lz.b.curvas.values() if k.tipo == "circulo")
    assert centros == [pytest.approx(q) for q in [(0, 0), (0, 10), (10, 0), (10, 10), (20, 0), (20, 10)]]
    assert lz.resultado.ok and lz.resultado.gdl == 3                    # se mueve solo el original (x, y, radio)
    lz = _lienzo(app_qt)
    ln = lz.b.agregar_linea((5, 0), (8, 0))
    lz.seleccion = [ln]
    lz.set_herramienta("patron_circular")
    lz.clics.append((None, (0, 0)))
    lz._procesar_clics()
    _aceptar(lz, "4", "360")
    assert _tipos(lz.b).count("linea") == 4 and lz.resultado.ok
    assert any(lz.b._extremos_linea(k) == (pytest.approx((0, 5)), pytest.approx((0, 8))) for k in lz.b.curvas)
    lz = _lienzo(app_qt)
    _crear(lz, "espiral", (0, 0), (2, 0))
    _aceptar(lz, "2", "3")
    s = lz.b.primitivas(next(iter(lz.b.curvas)))[0]
    assert evaluar_primitiva(s, dominio(s)[1])[0] == pytest.approx((8, 0))   # r = 2 + 3 · 2 vueltas


# ---------------------------------------------------------------- MODIFICAR
def _rect_restringido():
    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_restriccion("fijo", [b.curvas[ls[0]].p1])
    b.agregar_cota("distancia", [ls[0]], "20")
    b.agregar_cota("distancia", [ls[1]], "10")
    return b, ls


def test_empalme_r3_entre_dos_lineas_a_90_grados(app_qt):
    b, ls = _rect_restringido()
    lz = _lienzo(app_qt, b)
    lz.set_herramienta("empalme")
    lz.agregar_pick(ls[0], (15, 0))
    lz.agregar_pick(ls[1], (20, 5))
    _aceptar(lz, "3")
    arco = next(c for c in b.curvas.values() if c.tipo == "arco")
    centro = b.coords(arco.centro)
    assert b.radio(arco.id) == pytest.approx(3) and centro == pytest.approx((17, 3))
    for lid in ls[:2]:          # tangente: el centro queda a r de cada línea y el arco las toca en sus extremos
        assert abs(distancia_punto_recta(centro, *b._extremos_linea(lid))) == pytest.approx(3)
        assert set(b.curvas[lid].puntos()) & {arco.inicio, arco.fin}
    assert any(k.tipo == "radio" and k.expresion == "3" for k in b.cotas.values())
    assert lz.resultado.ok and lz.resultado.gdl == 0                    # sigue totalmente restringido
    assert _areas(b) == [pytest.approx(200 - (9 - math.pi * 9 / 4))]


def test_chaflanes(app_qt):
    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    ln = b.chaflan(ls[2], ls[3], 2)
    assert resolver(b, _valores(b)).ok and math.dist(*b._extremos_linea(ln)) == pytest.approx(2 * math.sqrt(2))
    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    ln = b.chaflan(ls[0], ls[1], 3, distancia2=1)
    assert resolver(b, _valores(b)).ok and math.dist(*b._extremos_linea(ln)) == pytest.approx(math.sqrt(10))
    b = Boceto()
    ls = b.agregar_rectangulo((0, 0), (20, 10))
    ln = b.chaflan(ls[0], ls[1], 2, angulo=60)
    (a, c) = b._extremos_linea(ln)
    assert resolver(b, _valores(b)).ok and abs(c[1] - a[1]) == pytest.approx(2 * math.tan(math.radians(60)))


def test_desfase_de_un_rectangulo_20x10_a_2mm_da_24x14(app_qt):
    lz = _lienzo(app_qt)
    _crear(lz, "rectangulo", (0, 0), (20, 10))
    linea = next(iter(lz.b.curvas))
    lz.b.agregar_restriccion("fijo", list(lz.b.curvas))
    lz.set_herramienta("desfase")
    lz.cursor = (10, -5)                                                # el ratón afuera del rectángulo
    lz.agregar_pick(linea, (10, 0))
    _aceptar(lz, "2")
    nuevas = [c for c in lz.b.curvas.values() if c.id > 12 and c.tipo == "linea"]
    pts = [lz.b.coords(p) for c in nuevas for p in c.puntos()]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    assert len(nuevas) == 4 and (max(xs) - min(xs), max(ys) - min(ys)) == (pytest.approx(24), pytest.approx(14))
    cota = next(k for k in lz.b.cotas.values() if k.tipo == "desfase")
    assert lz.resultado.ok and lz.resultado.gdl == 0                    # el desfase queda atado al original
    lz.editar_cota(cota.id, lz._pos_cursor)
    _aceptar(lz, "3")                                                   # la cota de desfase es paramétrica
    pts = [lz.b.coords(p) for c in nuevas for p in c.puntos()]
    assert max(q[0] for q in pts) - min(q[0] for q in pts) == pytest.approx(26)


def test_recortar_el_tramo_entre_dos_intersecciones(app_qt):
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (30, 0))
    lz.b.agregar_linea((10, -5), (10, 5))
    lz.b.agregar_linea((20, -5), (20, 5))
    lz.set_herramienta("recortar")
    lz.agregar_pick(l1, (15, 0))
    horizontales = sorted(lz.b._extremos_linea(k) for k, c in lz.b.curvas.items()
                          if c.tipo == "linea" and abs(lz.b._direccion(k)[1]) < 1e-9)
    assert horizontales == [((0, 0), (10, 0)), ((20, 0), (30, 0))]
    assert sum(r.tipo == "coincidente" for r in lz.b.restricciones.values()) == 2
    assert any(r.tipo == "colineal" for r in lz.b.restricciones.values()) and lz.resultado.ok
    c = lz.b.agregar_circulo((50, 0), 5)
    lz.b.agregar_linea((40, 0), (60, 0))
    lz.agregar_pick(c, (50, 5))                                          # el círculo cortado pasa a arco
    assert lz.b.tipo_de(c) == "arco" and lz.b.coords(lz.b.curvas[c].inicio) == pytest.approx((45, 0))
    suelta = lz.b.agregar_linea((0, 30), (5, 30))
    lz.agregar_pick(suelta, (2, 30))                                     # sin intersecciones: se borra
    assert suelta not in lz.b.curvas


def test_alargar_y_partir(app_qt):
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (5, 0))
    lz.b.agregar_linea((12, -5), (12, 5))
    lz.set_herramienta("alargar")
    lz.agregar_pick(l1, (4, 0))
    assert lz.b._extremos_linea(l1) == ((0, 0), (12, 0)) and lz.resultado.ok
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (30, 0))
    lz.b.agregar_linea((10, -5), (10, 5))
    lz.b.agregar_linea((20, -5), (20, 5))
    lz.set_herramienta("partir")
    lz.agregar_pick(l1, (15, 0))
    tramos = sorted(lz.b._extremos_linea(k) for k, c in lz.b.curvas.items()
                    if c.tipo == "linea" and abs(lz.b._direccion(k)[1]) < 1e-9)
    assert tramos == [((0, 0), (10, 0)), ((10, 0), (20, 0)), ((20, 0), (30, 0))] and lz.resultado.ok


def test_escala_y_mover_copiar(app_qt):
    lz = _lienzo(app_qt)
    ln = lz.b.agregar_linea((1, 1), (5, 1))
    lz.b.agregar_cota("distancia", [ln], "4")
    lz.resolver()
    lz.seleccion = [ln]
    lz.set_herramienta("escala")
    lz.clics.append((None, (1, 1)))
    lz._procesar_clics()
    _aceptar(lz, "2.5")
    assert lz.b._extremos_linea(ln) == (pytest.approx((1, 1)), pytest.approx((11, 1)))
    assert next(iter(lz.b.cotas.values())).expresion == "10" and lz.resultado.ok
    c = lz.b.agregar_circulo((0, 0), 2)
    lz.seleccion = [c]
    lz.opciones["copiar"] = True
    lz.set_herramienta("mover")
    for q in ((0, 0), (5, 3)):
        lz.clics.append((None, q))
        lz._procesar_clics()
    circulos = sorted(lz.b.coords(k.centro) for k in lz.b.curvas.values() if k.tipo == "circulo")
    assert circulos == [pytest.approx((0, 0)), pytest.approx((5, 3))]
    lz.opciones["copiar"] = False
    lz.seleccion = [c]
    lz.set_herramienta("mover")
    lz.clics.append((None, (0, 0)))
    lz._procesar_clics()
    _aceptar(lz, "0", "-4", "0")                                         # ΔX, ΔY, ángulo escritos
    assert lz.b.coords(lz.b.curvas[c].centro) == pytest.approx((0, -4))


def test_curva_de_fusion_g1_y_g2(app_qt):
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (10, 0))
    l2 = lz.b.agregar_linea((20, 5), (30, 5))
    lz.set_herramienta("curva_fusion")
    lz.agregar_pick(l1, (9, 0))
    lz.agregar_pick(l2, (21, 5))
    s = max(lz.b.curvas)
    prim = lz.b.primitivas(s)[0]
    _, d0 = evaluar_primitiva(prim, 0, 1)
    assert lz.b.tipo_de(s) == "spline" and abs(d0[1]) < 1e-9 and lz.resultado.ok    # sale tangente a la línea
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (10, 0))
    arco = b.agregar_arco_3_puntos((20, 5), (25, 10), (30, 5))
    s = b.curva_fusion(l1, (9, 0), arco, (20, 5), "G2")
    assert resolver(b).ok
    prim = b.primitivas(s)[0]
    t0, t1, _ = dominio(prim)
    _, d1, d2 = evaluar_primitiva(prim, t1, 2)
    k_spline = (d1[0] * d2[1] - d1[1] * d2[0]) / math.hypot(*d1) ** 3
    assert abs(k_spline) == pytest.approx(1 / b.radio(arco), rel=1e-5)   # misma curvatura que el arco (G2)


# ---------------------------------------------------------------- RESTRICCIONES
def test_poligono_curvatura_y_restricciones_con_curvas_nuevas(app_qt):
    lz = _lienzo(app_qt)
    ps = [lz.b.agregar_punto(*q) for q in ((0, 0), (10, 1), (11, 10), (-1, 9))]
    ls = [lz.b.agregar_linea(ps[i], ps[(i + 1) % 4]) for i in range(4)]
    lz.set_herramienta("r_poligono")
    lz.picks = []
    assert lz.aplicar_restriccion("poligono", [ls[0]])                   # un lado: toma la cadena cerrada
    largos = [math.dist(*lz.b._extremos_linea(k)) for k in ls]
    assert max(largos) - min(largos) < 1e-6
    d = [lz.b._direccion(k) for k in ls]
    assert abs(d[0][0] * d[1][0] + d[0][1] * d[1][1]) < 1e-6           # cuadrado: lados perpendiculares
    b = Boceto()
    s = b.agregar_spline([(0, 0), (10, 4), (20, 0)], "control")
    arco = b.agregar_arco_centro((20, -10), b.curvas[s].pts[-1], (30, -10))
    b.agregar_restriccion("curvatura", [s, arco])
    assert resolver(b).ok
    e = b.agregar_elipse((50, 0), (60, 0), 4)
    tangente = b.agregar_linea((40, 8), (70, 9))
    b.agregar_restriccion("tangente", [tangente, e])
    p = b.agregar_punto(10, 9)
    b.agregar_restriccion("coincidente", [p, s])
    c = b.agregar_circulo((52, 1), 2)
    b.agregar_restriccion("concentrica", [c, e])
    e2 = b.agregar_elipse((80, 0), (85, 0), 1)
    b.agregar_restriccion("igual", [e, e2])
    assert resolver(b).ok
    assert distancia_primitiva(b.primitivas(s)[0], b.coords(p)) < 1e-6
    assert distancia_primitiva(b.primitivas(e)[0], mas_cercano(b.primitivas(tangente)[0],
                                                               b.coords(b.curvas[e].centro))[2]) < 3
    assert b.primitivas(e2)[0][3:5] == pytest.approx(b.primitivas(e)[0][3:5])


@pytest.mark.parametrize("lados", [4, 6])
def test_poligono_circunscrito_par_queda_regular(app_qt, lados):
    """Con lados pares, «igual» + «tangente» dejaba un grado de libertad de más (hexágono: 5 en vez de 4); el editor
    suma la restricción de polígono regular, como `create_polygon` de la API."""
    lz = _lienzo(app_qt)
    lz._poligono((0, 0), (10, 0), lados, "circunscrito")
    assert grados_de_libertad(lz.b) == 4                                   # centro (2) + radio + giro


def test_restringir_automaticamente_hasta_gdl_cero(app_qt):
    b = Boceto()
    b.agregar_rectangulo((3, 4), (23, 14))
    b.agregar_circulo((13, 9), 2)
    agregado = auto_restringir(b)
    assert agregado and grados_de_libertad(b, _valores(b)) == 0 and resolver(b, _valores(b)).ok
    lz = _lienzo(app_qt)
    _crear(lz, "linea", (0, 0), (10, 0.05))
    assert lz.auto_restringir() and lz.resultado.gdl == 0


def test_linea_central_forma_perfiles_y_construccion_no(app_qt):
    lz = _lienzo(app_qt)
    lz.alternar_eje()
    _crear(lz, "rectangulo", (0, 0), (10, 10))
    assert all(c.eje for c in lz.b.curvas.values()) and _areas(lz.b) == [pytest.approx(100)]
    lz.seleccion = list(lz.b.curvas)
    lz.alternar_construccion()
    assert not lz.b.geometria() and len(lz.b.geometria(incluir_construccion=True)) == 4


# ---------------------------------------------------------------- Proyectar / Intersecar
def test_proyectar_e_intersecar(app_qt):
    lz = _lienzo(app_qt)
    assert lz.proyectar_forma(g.caja(10, 20, 5, (5, 5, 3)))
    assert _tipos(lz.b) == ["linea"] * 4                                  # arriba y abajo coinciden: una sola vez
    assert all(c.proyectada for c in lz.b.curvas.values()) and lz.resultado.gdl == 0
    assert _areas(lz.b) == [pytest.approx(200)]
    assert lz.proyectar_forma(g.cilindro(4, 10, (30, 0, -5)), "intersecar")
    assert any(c.tipo == "circulo" and c.radio == pytest.approx(4) for c in lz.b.curvas.values())
    lz.mostrar["proyectadas"] = False
    assert not any(lz._visible(c) for c in lz.b.curvas.values())
    prims, _ = proyectar_forma(g.cilindro(4, 10, (0, 0, -5)), g.Plano("XZ"))
    assert sorted(round(math.dist(p[2], p[3]), 6) for p in prims if p[0] == "linea") == [8, 8, 10]
    prims, puntos = intersecar_forma(g.caja(10, 10, 10), g.Plano.desde_marco((0, 0, 5), (0, 0, 1), (1, 0, 0)))
    assert len(prims) == 4 and not puntos


def test_proyectar_con_tipo_de_linea_construccion(app_qt):
    """Con «construcción» activa, lo proyectado nace de construcción (sin perfil) y se dibuja como tal;
    y alternar sobre lo ya proyectado cambia también cómo se ve."""
    lz = _lienzo(app_qt)
    lz.construccion = True
    assert lz.proyectar_forma(g.caja(10, 20, 5, (5, 5, 3)))
    assert all(c.proyectada and c.construccion for c in lz.b.curvas.values()) and _areas(lz.b) == []
    c = next(iter(lz.b.curvas.values()))
    assert lz._color_curva(c, set(), set())[0] != lz._color_curva(
        type("X", (), {"id": -1, "proyectada": True, "construccion": False, "eje": False,
                       "puntos": lambda self: []})(), set(), set())[0]
    lz.construccion = False
    lz.seleccion = list(lz.b.curvas)
    lz.alternar_construccion()                     # sobre lo seleccionado: vuelve a normal
    assert not any(c.construccion for c in lz.b.curvas.values()) and _areas(lz.b) == [pytest.approx(200)]


# ---------------------------------------------------------------- serialización y pestaña
def test_serializacion_de_las_entidades_nuevas_y_proyectos_viejos():
    b = Boceto()
    b.agregar_elipse((0, 0), (10, 0), 4)
    b.agregar_spline([(0, 0), (5, 5), (10, 0)], cerrada=False)
    b.agregar_conica((0, 0), (5, 5), (10, 0), 0.7)
    b.agregar_texto((0, 0), "Ab", 6, 15, negrita=True)
    b.agregar_proyeccion([("linea", None, (0, 0), (1, 1))])
    b.desfase(b.agregar_linea((0, 20), (10, 20)), 2)
    copia = Boceto.desde_dict(b.a_dict())
    assert copia.a_dict() == b.a_dict()
    viejo = {"siguiente_id": 4, "puntos": [{"id": 1, "x": 0, "y": 0}, {"id": 2, "x": 5, "y": 0}],
             "curvas": [{"tipo": "linea", "id": 3, "p1": 1, "p2": 2, "construccion": False}],
             "restricciones": [], "cotas": []}
    ln = Boceto.desde_dict(viejo).curvas[3]
    assert not ln.eje and not ln.proyectada


def test_la_pestana_boceto_no_tiene_items_grisados(app_qt):
    from omnicad.ui.cinta_boceto import GRUPOS_BOCETO
    from omnicad.ui.modo_boceto import ACCIONES_BOCETO
    claves = {a[0] for a in ACCIONES_BOCETO} | {"sk_terminar", "sk_construccion", "sk_eje", "sk_autorestringir",
                                                "parametros"}

    def items(lista):
        for it in lista:
            if it == "-":
                continue
            if it[0] == "sub":
                yield from items(it[2])
            else:
                yield it
    usados = []
    for _titulo, rapidos, lista in GRUPOS_BOCETO:
        assert all(isinstance(r, str) and r in claves for r in rapidos)
        usados += [it[2] for it in items(lista)]
    assert all(c in claves for c in usados), [c for c in usados if c not in claves]
    atajos = {a[3] for a in ACCIONES_BOCETO if a[3]}
    assert {"L", "R", "C", "D", "T", "O", "P", "M", "Shift+V"} <= atajos


def test_deshacer_recorte_y_entrada_que_no_rompe_atajos(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (30, 0))
    lz.b.agregar_linea((10, -5), (10, 5))
    lz.set_herramienta("recortar")
    lz.agregar_pick(l1, (5, 0))
    assert lz.b._extremos_linea(l1) == ((10, 0), (30, 0))
    lz.deshacer()
    assert lz.b._extremos_linea(l1) == ((0, 0), (30, 0))
    lz.set_herramienta("linea")
    lz.clics = [(None, (0.0, 0.0))]
    evento = QKeyEvent(QKeyEvent.Type.ShortcutOverride, Qt.Key_2, Qt.NoModifier, "2")
    assert lz.event(evento) and evento.isAccepted()                     # el dígito es de la entrada dinámica


# ---------------------------------------------------------------- entradas no finitas y cotas fuera de rango
def test_detectar_salta_primitivas_no_finitas():
    import faulthandler
    nan, inf = float("nan"), float("inf")
    faulthandler.dump_traceback_later(60, exit=True)     # si vuelve el cuelgue del Splitter de OCC, pytest muere
    try:
        assert detectar([("linea", 1, (0, 0), (nan, 5))], PLANO) == []
        perfiles = detectar([("linea", 1, (0, 0), (inf, 5)), ("circulo", 2, (0, 0), 5.0),
                             ("spline", 3, ((0, 0), (nan, 1), (2, 0)), (0, 0, 0, 1, 1, 1), 2, None)], PLANO)
    finally:
        faulthandler.cancel_dump_traceback_later()
    assert [round(p.area, 6) for p in perfiles] == [pytest.approx(math.pi * 25)] and perfiles[0].firma == {2}
    assert g.es_valida(perfiles[0].cara)


def test_boceto_rechaza_numeros_no_finitos_y_spline_degenerada():
    nan, inf = float("nan"), float("inf")
    b = Boceto()
    for crear in (lambda: b.agregar_punto(nan, 0), lambda: b.agregar_punto(0, inf),
                  lambda: b.agregar_linea((0, 0), (nan, 1)), lambda: b.agregar_circulo((0, 0), nan),
                  lambda: b.agregar_circulo((0, 0), inf), lambda: b.agregar_circulo((inf, 0), 3),
                  lambda: b.agregar_elipse((0, 0), (5, 0), nan), lambda: b.agregar_texto((0, 0), "A", nan),
                  lambda: b.agregar_spline([(1, 1), (1, 1), (1, 1)])):
        with pytest.raises(ErrorBoceto):
            crear()
    assert not b.curvas
    sid = b.agregar_spline([(1, 1), (1, 1), (4, 2)])                # puntos repetidos pero no todos: vale
    assert len(b.curvas[sid].pts) == 3


def test_validar_valor_cota():
    for tipo, valor in (("radio", -5), ("radio", 0), ("diametro", -1), ("distancia", float("nan")),
                        ("distancia_h", -2), ("desfase", 0), ("radio", 1e9), ("distancia", 1.5e6), ("diametro", math.inf)):
        with pytest.raises(ErrorBoceto):
            validar_valor_cota(tipo, valor)
    for tipo, valor in (("radio", 5), ("radio", 6e4), ("diametro", 1e6), ("distancia", 1.5e5), ("distancia_v", 1e6),
                        ("desfase", 0.1), ("angulo", 120), ("angulo", -30)):
        validar_valor_cota(tipo, valor)


def test_detectar_perfiles_grandes_dentro_del_tope():
    """Toda región cerrada dentro del tope de las cotas (±1 km) forma perfil: con la cara vieja de 1e5 mm, un
    círculo de 60 m de radio desaparecía sin aviso."""
    for r in (6e4, 9e5):
        perfiles = detectar([("circulo", 1, (0, 0), r)], PLANO)
        assert len(perfiles) == 1 and perfiles[0].area == pytest.approx(math.pi * r * r, rel=1e-9)
        assert g.es_valida(perfiles[0].cara)
    assert detectar([("circulo", 1, (0, 0), 1e300)], PLANO) == []      # absurdo: queda afuera, sin colgarse


def test_cota_negativa_o_cero_se_rechaza_en_la_caja(app_qt):
    lz = _lienzo(app_qt)
    c = lz.b.agregar_circulo((20, 20), 5)
    lz._abrir_cota("radio", [c], lz._pos_cursor)
    _aceptar(lz, "-5")
    assert not lz.b.cotas and lz.entrada is not None                    # la caja queda abierta (en rojo), como Fusion
    _aceptar(lz, "4")
    assert [k.expresion for k in lz.b.cotas.values()] == ["4"] and lz.b.radio(c) == pytest.approx(4)
    cota = next(iter(lz.b.cotas))
    lz.editar_cota(cota, lz._pos_cursor)
    _aceptar(lz, "0")
    assert lz.b.cotas[cota].expresion == "4" and lz.entrada is not None and lz.b.radio(c) == pytest.approx(4)
    _aceptar(lz, "3")
    assert lz.b.cotas[cota].expresion == "3" and lz.b.radio(c) == pytest.approx(3)


def test_lo_escrito_al_dibujar_respeta_el_tope_de_las_cotas(app_qt):
    """Lo escrito en la caja al dibujar se vuelve cota: el mismo rango que al editarla (> 0 y hasta 1 km)."""
    lz = _lienzo(app_qt)
    lz.set_herramienta("circulo")
    lz._registrar_clic(None, (0.0, 0.0))                                 # centro
    for malo in ("3000000", "0", "-2"):
        with pytest.raises(ErrorBoceto):
            lz._evaluar_campo("diametro", malo)
    with pytest.raises(ErrorBoceto, match="1.000.000"):
        lz._evaluar_campo("largo", "2e6")
    assert lz._evaluar_campo("angulo", "-30") == pytest.approx(-30)      # los ángulos no tienen este tope
    lz._bloquear("diametro", "50", lz._evaluar_campo("diametro", "50"))
    lz._registrar_clic(None, (5.0, 0.0))
    assert [(k.tipo, k.expresion) for k in lz.b.cotas.values()] == [("diametro", "50")]
    perfiles = detectar(lz.b.geometria(), PLANO)
    assert len(perfiles) == 1 and g.es_valida(perfiles[0].cara)
    assert g.area(perfiles[0].cara) == pytest.approx(math.pi * 25 ** 2, rel=1e-6)


def test_simetria_de_elipses_y_splines_y_punto_medio_de_arco():
    b = Boceto()
    eje = b.agregar_linea((0, -20), (0, 20))
    b.agregar_restriccion("fijo", [eje])
    e1 = b.agregar_elipse((5, 0), (12, 1), 3, ejes=False)
    e2 = b.agregar_elipse((-6, 1), (-13, 0), 2, ejes=False)
    b.agregar_restriccion("simetrica", [e1, e2, eje])
    s1 = b.agregar_spline([(2, 5), (6, 9), (10, 5)])
    s2 = b.agregar_spline([(-10, 6), (-6, 10), (-2, 5)])
    b.agregar_restriccion("simetrica", [s1, s2, eje])
    arco = b.agregar_arco_3_puntos((20, 0), (25, 5), (30, 0))
    p = b.agregar_punto(24, 7)
    b.agregar_restriccion("punto_medio", [p, arco])
    assert resolver(b).ok
    (c1, a1, b1, _), (c2, a2, b2, _) = b.primitivas(e1)[0][2:6], b.primitivas(e2)[0][2:6]
    assert c2 == pytest.approx((-c1[0], c1[1])) and (a1, b1) == pytest.approx((a2, b2))
    for q1, q2 in zip(b.curvas[s1].pts, b.curvas[s2].pts[::-1], strict=True):
        assert b.coords(q2) == pytest.approx((-b.coords(q1)[0], b.coords(q1)[1]))
    prim = b.primitivas(arco)[0]
    assert b.coords(p) == pytest.approx(evaluar_primitiva(prim, dominio(prim)[1] / 2)[0])
