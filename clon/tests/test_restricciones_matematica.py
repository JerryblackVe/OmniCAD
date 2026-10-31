# -*- coding: utf-8 -*-
"""Cada restricción del boceto, probada con su invariante matemática (medida aparte del solver, con las fórmulas de
la geometría analítica), antes y después de arrastrar un punto, y con la prueba de que al quitarla vuelven los grados
de libertad. Tolerancia: 1e-6 mm (la del solver: `TOLERANCIA`)."""
import math

import pytest

from omnicad import api
from omnicad.restricciones import Boceto, ErrorBoceto, grados_de_libertad, resolver
from omnicad.restricciones.boceto import dominio, evaluar_primitiva

TOL = 1e-6      # mm: TOLERANCIA del solver; las medidas son residuos en mm
ANG = 1e-7      # rad: producto vectorial / escalar normalizado


def _p(b, i):
    return b.coords(i)


def _arrastrar(b, pid, x, y):
    """Lo que hace el editor al arrastrar: pone el punto donde está el ratón y resuelve respetándolo."""
    b.puntos[pid].x, b.puntos[pid].y = x, y
    return resolver(b, {}, arrastrado=pid)


def _unit(a, c):
    d = math.dist(a, c)
    return ((c[0] - a[0]) / d, (c[1] - a[1]) / d)


def _dist_recta(q, a, c):
    """Distancia con signo del punto q a la recta que pasa por a y c."""
    u = _unit(a, c)
    return (q[0] - a[0]) * -u[1] + (q[1] - a[1]) * u[0]


def _dir(b, lid):
    c = b.curvas[lid]
    return _unit(_p(b, c.p1), _p(b, c.p2))


def _cruz(u, v):
    return u[0] * v[1] - u[1] * v[0]


def _punto(u, v):
    return u[0] * v[0] + u[1] * v[1]


def _largo(b, lid):
    c = b.curvas[lid]
    return math.dist(_p(b, c.p1), _p(b, c.p2))


def _centro_radio(b, cid):
    c = b.curvas[cid]
    return _p(b, c.centro), b.radio(cid)


def _esq(b):
    """Cuatro puntos sueltos lejos del origen (nada los ancla)."""
    return [b.agregar_punto(40 + 10 * i, 25 + 7 * (i % 2)) for i in range(4)]


# Cada escenario: construye el boceto SIN la restricción y devuelve (b, tipo, entidades, comprobar, mover):
#   comprobar(b): lanza AssertionError si el invariante no se cumple
#   mover: lista de (punto, x, y) con las que se arrastra después de aplicar la restricción
def _horizontal():
    b = Boceto()
    a, c = b.agregar_punto(40, 30), b.agregar_punto(55, 38)
    l = b.agregar_linea(a, c)
    return b, "horizontal", [l], lambda: abs(_p(b, a)[1] - _p(b, c)[1]) < TOL, [(c, 60, 52), (a, 20, 5)], 1


def _vertical():
    b = Boceto()
    a, c = b.agregar_punto(40, 30), b.agregar_punto(46, 48)
    l = b.agregar_linea(a, c)
    return b, "vertical", [l], lambda: abs(_p(b, a)[0] - _p(b, c)[0]) < TOL, [(c, 52, 70), (a, 20, 5)], 1


def _coincidente_puntos():
    b = Boceto()
    l1 = b.agregar_linea((40, 30), (60, 40))
    l2 = b.agregar_linea((64, 43), (80, 20))
    e1, e2 = b.curvas[l1].p2, b.curvas[l2].p1
    return b, "coincidente", [e1, e2], lambda: math.dist(_p(b, e1), _p(b, e2)) < TOL, [(e2, 90, 70), (e1, 33, 12)], 2


def _coincidente_linea():
    b = Boceto()
    l = b.agregar_linea((40, 30), (80, 50))
    q = b.agregar_punto(60, 45)
    a, c = b.curvas[l].p1, b.curvas[l].p2
    return b, "coincidente", [q, l], lambda: abs(_dist_recta(_p(b, q), _p(b, a), _p(b, c))) < TOL, [(q, 70, 20), (c, 90, 90)], 1


def _coincidente_circulo():
    b = Boceto()
    k = b.agregar_circulo((60, 40), 12)
    q = b.agregar_punto(80, 45)
    return (b, "coincidente", [q, k], lambda: abs(math.dist(_p(b, q), _p(b, b.curvas[k].centro)) - b.radio(k)) < TOL,
            [(q, 30, 60)], 1)


def _tangente_linea_circulo():
    b = Boceto()
    k = b.agregar_circulo((60, 40), 12)
    l = b.agregar_linea((30, 70), (90, 62))
    a, c = b.curvas[l].p1, b.curvas[l].p2
    return (b, "tangente", [l, k], lambda: abs(abs(_dist_recta(_centro_radio(b, k)[0], _p(b, a), _p(b, c)))
                                                - b.radio(k)) < TOL, [(a, 20, 80), (c, 95, 75)], 1)


def _tangente_linea_arco():
    b = Boceto()
    k = b.agregar_arco_centro((60, 40), (72, 40), (60, 52))
    l = b.agregar_linea((30, 70), (90, 62))
    a, c = b.curvas[l].p1, b.curvas[l].p2
    return (b, "tangente", [l, k], lambda: abs(abs(_dist_recta(_centro_radio(b, k)[0], _p(b, a), _p(b, c)))
                                                - b.radio(k)) < TOL, [(a, 20, 80)], 1)


def _tangente_arcos_exterior():
    b = Boceto()
    k1 = b.agregar_circulo((50, 40), 10)
    k2 = b.agregar_circulo((75, 40), 8)
    return (b, "tangente", [k1, k2], lambda: abs(math.dist(_centro_radio(b, k1)[0], _centro_radio(b, k2)[0])
                                                  - (b.radio(k1) + b.radio(k2))) < TOL,
            [(b.curvas[k2].centro, 90, 70)], 1)


def _tangente_arcos_interior():
    b = Boceto()
    k1 = b.agregar_circulo((50, 40), 20)
    k2 = b.agregar_circulo((55, 42), 6)
    return (b, "tangente", [k1, k2], lambda: abs(math.dist(_centro_radio(b, k1)[0], _centro_radio(b, k2)[0])
                                                  - abs(b.radio(k1) - b.radio(k2))) < TOL,
            [(b.curvas[k2].centro, 58, 44)], 1)


def _tangente_encadenadas():
    """Línea y arco que comparten un extremo: la tangente se mide en la unión (tangentes paralelas)."""
    b = Boceto()
    j = b.agregar_punto(60, 40)
    l = b.agregar_linea((30, 30), j)
    k = b.agregar_arco_centro((62, 52), j, (74, 52))
    def ok():
        ul = _dir(b, l)
        radial = _unit(_p(b, b.curvas[k].centro), _p(b, j))                     # radio al punto de unión
        return abs(_punto(ul, radial)) < ANG * 10          # la línea es perpendicular al radio ⇒ tangente
    return b, "tangente", [l, k], ok, [(b.curvas[l].p1, 20, 10)], 1


def _igual_lineas():
    b = Boceto()
    l1 = b.agregar_linea((40, 30), (60, 34))
    l2 = b.agregar_linea((45, 60), (95, 90))
    return b, "igual", [l1, l2], lambda: abs(_largo(b, l1) - _largo(b, l2)) < TOL, [(b.curvas[l2].p2, 120, 100)], 1


def _igual_circulos():
    b = Boceto()
    k1, k2 = b.agregar_circulo((40, 40), 9), b.agregar_circulo((90, 40), 15)
    return b, "igual", [k1, k2], lambda: abs(b.radio(k1) - b.radio(k2)) < TOL, [(b.curvas[k2].centro, 100, 60)], 1


def _igual_arcos():
    b = Boceto()
    k1 = b.agregar_arco_centro((40, 40), (50, 40), (40, 50))
    k2 = b.agregar_arco_centro((90, 40), (105, 40), (90, 55))
    return b, "igual", [k1, k2], lambda: abs(b.radio(k1) - b.radio(k2)) < TOL, [(b.curvas[k2].centro, 100, 60)], 1


def _paralela():
    b = Boceto()
    l1 = b.agregar_linea((40, 30), (80, 35))
    l2 = b.agregar_linea((45, 70), (70, 100))
    return (b, "paralela", [l1, l2], lambda: abs(_cruz(_dir(b, l1), _dir(b, l2))) < ANG,
            [(b.curvas[l1].p2, 80, 60), (b.curvas[l2].p1, 30, 90)], 1)


def _perpendicular():
    b = Boceto()
    l1 = b.agregar_linea((40, 30), (80, 35))
    l2 = b.agregar_linea((45, 70), (70, 100))
    return (b, "perpendicular", [l1, l2], lambda: abs(_punto(_dir(b, l1), _dir(b, l2))) < ANG,
            [(b.curvas[l1].p2, 80, 60), (b.curvas[l2].p1, 30, 90)], 1)


def _punto_medio_linea():
    b = Boceto()
    l = b.agregar_linea((40, 30), (90, 50))
    q = b.agregar_punto(70, 48)
    a, c = b.curvas[l].p1, b.curvas[l].p2
    return (b, "punto_medio", [q, l],
            lambda: math.dist(_p(b, q), ((_p(b, a)[0] + _p(b, c)[0]) / 2, (_p(b, a)[1] + _p(b, c)[1]) / 2)) < TOL,
            [(c, 130, 90), (a, 10, 5)], 2)


def _punto_medio_arco():
    b = Boceto()
    k = b.agregar_arco_centro((60, 40), (80, 40), (60, 60))
    q = b.agregar_punto(70, 70)

    def ok():
        prim = b.primitivas(k)[0]
        m = evaluar_primitiva(prim, dominio(prim)[1] / 2)[0]
        return math.dist(_p(b, q), m) < TOL
    return b, "punto_medio", [q, k], ok, [(b.curvas[k].fin, 40, 60)], 2


def _concentrica():
    b = Boceto()
    k1 = b.agregar_circulo((40, 40), 9)
    k2 = b.agregar_arco_centro((90, 60), (105, 60), (90, 75))
    return (b, "concentrica", [k1, k2],
            lambda: math.dist(_centro_radio(b, k1)[0], _centro_radio(b, k2)[0]) < TOL,
            [(b.curvas[k2].centro, 100, 20)], 2)


def _colineal():
    b = Boceto()
    l1 = b.agregar_linea((40, 30), (80, 35))
    l2 = b.agregar_linea((100, 70), (130, 90))
    a, c = b.curvas[l1].p1, b.curvas[l1].p2

    def ok():
        return all(abs(_dist_recta(_p(b, q), _p(b, a), _p(b, c))) < TOL for q in (b.curvas[l2].p1, b.curvas[l2].p2))
    return b, "colineal", [l1, l2], ok, [(c, 80, 50), (b.curvas[l2].p2, 150, 20)], 2


def _simetria_puntos():
    b = Boceto()
    eje = b.agregar_linea((60, 20), (60, 90))
    p, q = b.agregar_punto(40, 50), b.agregar_punto(85, 62)
    a, c = b.curvas[eje].p1, b.curvas[eje].p2

    def ok():
        P, Q = _p(b, p), _p(b, q)
        medio = ((P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2)
        u = _unit(_p(b, a), _p(b, c))
        return abs(_dist_recta(medio, _p(b, a), _p(b, c))) < TOL and abs(_punto(u, (Q[0] - P[0], Q[1] - P[1]))) < TOL
    return b, "simetrica", [p, q, eje], ok, [(p, 30, 40), (c, 70, 100)], 2


def _simetria_lineas():
    b = Boceto()
    eje = b.agregar_linea((60, 20), (60, 90))
    l1, l2 = b.agregar_linea((40, 30), (45, 70)), b.agregar_linea((82, 28), (70, 66))
    a, c = b.curvas[eje].p1, b.curvas[eje].p2

    def reflejo(q):
        u = _unit(_p(b, a), _p(b, c))
        A = _p(b, a)
        t = (q[0] - A[0]) * u[0] + (q[1] - A[1]) * u[1]
        f = (A[0] + t * u[0], A[1] + t * u[1])
        return 2 * f[0] - q[0], 2 * f[1] - q[1]

    def ok():
        P = [_p(b, b.curvas[l1].p1), _p(b, b.curvas[l1].p2)]
        Q = [_p(b, b.curvas[l2].p1), _p(b, b.curvas[l2].p2)]
        directo = sum(math.dist(reflejo(x), y) for x, y in zip(P, Q, strict=True))
        inverso = sum(math.dist(reflejo(x), y) for x, y in zip(P, Q[::-1], strict=True))
        return min(directo, inverso) < 4 * TOL
    return b, "simetrica", [l1, l2, eje], ok, [(b.curvas[l1].p1, 35, 20)], 4        # 2 extremos × 2 coordenadas


def _simetria_circulos():
    b = Boceto()
    eje = b.agregar_linea((60, 20), (60, 90))
    k1, k2 = b.agregar_circulo((40, 50), 9), b.agregar_circulo((88, 58), 14)
    a, c = b.curvas[eje].p1, b.curvas[eje].p2

    def ok():
        P, Q = _centro_radio(b, k1), _centro_radio(b, k2)
        medio = ((P[0][0] + Q[0][0]) / 2, (P[0][1] + Q[0][1]) / 2)
        return (abs(_dist_recta(medio, _p(b, a), _p(b, c))) < TOL and abs(P[1] - Q[1]) < TOL)
    return b, "simetrica", [k1, k2, eje], ok, [(b.curvas[k1].centro, 30, 30)], 3


def _poligono():
    b = Boceto()
    pts = [b.agregar_punto(*p) for p in [(40, 30), (70, 33), (78, 62), (52, 80), (32, 58)]]
    ls = [b.agregar_linea(pts[i], pts[(i + 1) % 5]) for i in range(5)]

    def ok():
        P = [_p(b, q) for q in pts]
        cx, cy = sum(x for x, _ in P) / 5, sum(y for _, y in P) / 5
        radios = [math.hypot(x - cx, y - cy) for x, y in P]
        lados = [math.dist(P[i], P[(i + 1) % 5]) for i in range(5)]
        angulos = []
        for i in range(5):
            a = math.atan2(P[i][1] - cy, P[i][0] - cx)
            c = math.atan2(P[(i + 1) % 5][1] - cy, P[(i + 1) % 5][0] - cx)
            angulos.append((c - a) % (2 * math.pi))
        return (max(radios) - min(radios) < TOL and max(lados) - min(lados) < TOL
                and all(abs(t - 2 * math.pi / 5) < 1e-6 for t in angulos))
    return b, "poligono", ls, ok, [(pts[0], 30, 20), (pts[2], 95, 70)], 6


ESCENARIOS = {
    "horizontal": _horizontal, "vertical": _vertical, "coincidente_puntos": _coincidente_puntos,
    "coincidente_linea": _coincidente_linea, "coincidente_circulo": _coincidente_circulo,
    "tangente_linea_circulo": _tangente_linea_circulo, "tangente_linea_arco": _tangente_linea_arco,
    "tangente_circulos_ext": _tangente_arcos_exterior, "tangente_circulos_int": _tangente_arcos_interior,
    "tangente_encadenadas": _tangente_encadenadas, "igual_lineas": _igual_lineas, "igual_circulos": _igual_circulos,
    "igual_arcos": _igual_arcos, "paralela": _paralela, "perpendicular": _perpendicular,
    "punto_medio_linea": _punto_medio_linea, "punto_medio_arco": _punto_medio_arco, "concentrica": _concentrica,
    "colineal": _colineal, "simetria_puntos": _simetria_puntos, "simetria_lineas": _simetria_lineas,
    "simetria_circulos": _simetria_circulos, "poligono": _poligono,
}


@pytest.mark.parametrize("nombre", list(ESCENARIOS))
def test_restriccion_cumple_su_invariante(nombre):
    b, tipo, ents, cumple, mover, gdl_quita = ESCENARIOS[nombre]()
    assert resolver(b, {}).ok
    gdl_antes = grados_de_libertad(b)
    rid = b.agregar_restriccion(tipo, ents)
    r = resolver(b, {})
    assert r.ok, r.descripcion()
    assert cumple(), f"{nombre}: no se cumple al aplicar"
    assert gdl_antes - r.gdl == gdl_quita, f"{nombre}: quitó {gdl_antes - r.gdl} GDL, se esperaban {gdl_quita}"
    for pid, x, y in mover:                            # arrastrar: la relación se conserva
        r = _arrastrar(b, pid, x, y)
        assert r.ok, f"{nombre}: arrastrar a ({x}, {y}) dejó el boceto en conflicto: {r.descripcion()}"
        assert cumple(), f"{nombre}: se perdió al arrastrar {pid} a ({x}, {y})"
    b.eliminar(rid)                                     # quitarla: vuelven los GDL y las entidades siguen
    r = resolver(b, {})
    assert r.ok and r.gdl == gdl_antes, f"{nombre}: al quitarla quedan {r.gdl} GDL, eran {gdl_antes}"
    assert not b.restricciones


def test_fijo_no_se_mueve_y_se_libera():
    b = Boceto()
    a, c = b.agregar_punto(40, 30), b.agregar_punto(70, 45)
    b.agregar_linea(a, c)
    gdl = grados_de_libertad(b)
    rid = b.agregar_restriccion("fijo", [a])
    assert resolver(b, {}).gdl == gdl - 2
    r = _arrastrar(b, c, 90, 90)                       # se arrastra el otro extremo: el fijo no se entera
    assert r.ok and _p(b, a) == pytest.approx((40, 30), abs=TOL) and _p(b, c) == pytest.approx((90, 90), abs=TOL)
    b.eliminar(rid)
    assert resolver(b, {}).gdl == gdl
    _arrastrar(b, a, 20, 10)                           # liberado: ahora sí se mueve
    assert _p(b, a) == pytest.approx((20, 10), abs=TOL)


def test_fijo_en_linea_deja_los_dos_extremos():
    b = Boceto()
    l = b.agregar_linea((40, 30), (70, 45))
    gdl = grados_de_libertad(b)
    b.agregar_restriccion("fijo", [l])
    assert resolver(b, {}).gdl == gdl - 4


def _escenario_curvatura():
    """Spline (ajuste) y arco que se unen en el punto j: la curvatura pide una curva libre y otra encadenada."""
    b = Boceto()
    j = b.agregar_punto(60, 40)
    sp = b.agregar_spline([(20, 20), (35, 30), j])
    ar = b.agregar_arco_centro((60, 55), j, (75, 55))
    return b, sp, ar, j


def g2_en_la_union(b, sp, ar, j):
    """(tangentes, curvaturas) en la unión, medidas con κ = (x′y″ − y′x″)/|v|³ aparte del solver: cada curva recorrida
    alejándose de j; hay G2 si las tangentes son opuestas y las curvaturas con signo suman cero."""
    def extremo(cid):
        prim = b.primitivas(cid)[0]
        t0, t1, _ = dominio(prim)
        ini = b.curvas[cid].extremos()[0]
        _c, d1, d2 = evaluar_primitiva(prim, t0 if ini == j else t1, 2)
        s = 1.0 if ini == j else -1.0
        n = math.hypot(*d1)
        return (s * d1[0] / n, s * d1[1] / n), s * _cruz(d1, d2) / n ** 3
    (ta, ka), (tb, kb) = extremo(sp), extremo(ar)
    return abs(_cruz(ta, tb)) < 1e-6 and _punto(ta, tb) < 0, ka, kb


def _curvatura():
    b, sp, ar, j = _escenario_curvatura()

    def cumple():
        g1, ka, kb = g2_en_la_union(b, sp, ar, j)
        return g1 and abs(ka + kb) < 1e-5
    return b, "curvatura", [sp, ar], cumple, [(b.curvas[ar].fin, 80, 62), (b.curvas[sp].pts[0], 15, 25)], 2


ESCENARIOS["curvatura"] = _curvatura


def test_curvatura_g2_en_la_union_spline_arco():
    b, sp, ar, j = _escenario_curvatura()
    antes = g2_en_la_union(b, sp, ar, j)
    assert not (antes[0] and abs(antes[1] + antes[2]) < 1e-5)       # sin la restricción no hay G2 por casualidad
    b.agregar_restriccion("curvatura", [sp, ar])
    r = resolver(b, {})
    assert r.ok, r.descripcion()
    g1, ka, kb = g2_en_la_union(b, sp, ar, j)
    assert g1, "las tangentes no son opuestas: no hay ni G1"
    assert abs(ka + kb) < 1e-5, f"curvaturas {ka} y {kb}: no hay G2"


def test_curvatura_se_conserva_al_arrastrar_y_se_libera_al_quitarla():
    b, sp, ar, j = _escenario_curvatura()
    gdl0 = grados_de_libertad(b)
    rid = b.agregar_restriccion("curvatura", [sp, ar])
    quita = gdl0 - resolver(b, {}).gdl
    assert quita >= 2                                               # tangente (1) + curvatura (1) por lo menos
    for pid, x, y in ((b.curvas[ar].fin, 80, 62), (b.curvas[sp].pts[0], 15, 25)):
        assert _arrastrar(b, pid, x, y).ok
        g1, ka, kb = g2_en_la_union(b, sp, ar, j)
        assert g1 and abs(ka + kb) < 1e-4, (pid, ka, kb)
    b.eliminar(rid)
    assert resolver(b, {}).gdl == gdl0


def test_poligono_exige_cadena_cerrada_y_lineas():
    b = Boceto()
    l1, l2, l3 = (b.agregar_linea((i * 10, 0), (i * 10 + 8, 5)) for i in range(3))
    with pytest.raises(ErrorBoceto):
        b.agregar_restriccion("poligono", [l1, l2, l3])               # cadena abierta
    k = b.agregar_circulo((100, 100), 5)
    with pytest.raises(ErrorBoceto):
        b.agregar_restriccion("poligono", [l1, l2, k])


# ---------------------------------------------------------------- sobre-definición: redundante ≠ contradictoria
def _tres_lineas():
    b = Boceto()
    return b, [b.agregar_linea((40 + 10 * i, 30 + 15 * i), (80 + 10 * i, 36 + 15 * i + 3 * i)) for i in range(3)]


def test_una_restriccion_repetida_es_redundante_y_no_un_conflicto():
    from omnicad.restricciones import restricciones_redundantes
    b, (l1, _l2, _l3) = _tres_lineas()
    primera = b.agregar_restriccion("horizontal", [l1])
    segunda = b.agregar_restriccion("horizontal", [l1])
    r = resolver(b, {})
    assert r.ok                                        # no hay contradicción: se puede cumplir
    assert restricciones_redundantes(b) == [segunda]   # sobra la repetida, no la primera
    b.eliminar(segunda)
    assert restricciones_redundantes(b) == [] and primera in b.restricciones


def test_tres_paralelas_que_se_implican_marcan_solo_la_que_sobra():
    from omnicad.restricciones import restricciones_redundantes
    b, (l1, l2, l3) = _tres_lineas()
    ids = [b.agregar_restriccion("paralela", [x, y]) for x, y in ((l1, l2), (l2, l3), (l1, l3))]
    assert resolver(b, {}).ok
    assert restricciones_redundantes(b) == [ids[2]]


def test_sin_redundancia_devuelve_lista_vacia_y_en_conflicto_tambien():
    from omnicad.restricciones import restricciones_redundantes
    b, (l1, l2, _l3) = _tres_lineas()
    b.agregar_restriccion("horizontal", [l1])
    b.agregar_restriccion("paralela", [l1, l2])
    assert restricciones_redundantes(b) == []
    b.agregar_restriccion("perpendicular", [l1, l2])   # contradice la paralela: sin solución
    assert not resolver(b.copia(), {}).ok
    assert restricciones_redundantes(b) == []          # de los conflictos se ocupa restricciones_en_conflicto


# ---------------------------------------------------------------- conflictos, degenerados y referencias rotas
def test_horizontal_sobre_vertical_colapsa_y_se_informa():
    b = Boceto()
    l = b.agregar_linea((40, 30), (40, 70))
    b.agregar_restriccion("vertical", [l])
    b.agregar_restriccion("horizontal", [l])
    r = resolver(b, {})
    assert not r.ok and "colapsa" in r.mensaje or not r.ok       # no se "cumple" achicando la línea a largo cero


def test_paralela_y_perpendicular_a_la_vez_son_una_contradiccion():
    from omnicad.restricciones.solver import restricciones_en_conflicto
    b, (l1, l2, _l3) = _tres_lineas()
    p = b.agregar_restriccion("paralela", [l1, l2])
    q = b.agregar_restriccion("perpendicular", [l1, l2])
    assert not resolver(b.copia(), {}).ok
    assert set(restricciones_en_conflicto(b, {})) == {p, q}       # cualquiera de las dos resuelve el choque


INCOMPATIBLES = {                    # tipo → una selección que no le corresponde (las 14 del menú, con H y V aparte)
    "horizontal": "circulo", "vertical": "dos_puntos_y_linea", "coincidente": "dos_lineas", "tangente": "dos_lineas",
    "igual": "linea_circulo", "paralela": "linea_circulo", "perpendicular": "dos_circulos", "fijo": "nada",
    "punto_medio": "dos_puntos", "concentrica": "dos_lineas", "colineal": "dos_circulos", "simetrica": "dos_puntos",
    "curvatura": "dos_lineas", "poligono": "dos_lineas"}


@pytest.mark.parametrize("tipo", list(INCOMPATIBLES))
def test_seleccion_incompatible_se_rechaza_con_mensaje_y_no_deja_nada(tipo):
    b = Boceto()
    p, q = b.agregar_punto(40, 30), b.agregar_punto(60, 80)
    l1, l2 = b.agregar_linea((50, 30), (80, 40)), b.agregar_linea((50, 60), (90, 50))
    k, k2 = b.agregar_circulo((120, 40), 9), b.agregar_circulo((150, 40), 5)
    elegidas = {"circulo": [k], "dos_puntos_y_linea": [p, q, l1], "dos_lineas": [l1, l2], "linea_circulo": [l1, k],
                "dos_circulos": [k, k2], "nada": [], "dos_puntos": [p, q]}[INCOMPATIBLES[tipo]]
    with pytest.raises(ErrorBoceto) as e:
        b.agregar_restriccion(tipo, elegidas)
    assert e.value.args[0]                                             # dice por qué
    assert not b.restricciones


def test_misma_entidad_dos_veces_o_inexistente_se_rechaza():
    b, (l1, _l2, _l3) = _tres_lineas()
    with pytest.raises(ErrorBoceto):
        b.agregar_restriccion("paralela", [l1, l1])
    with pytest.raises(Exception):  # noqa: B017 — una entidad que no existe: KeyError o ErrorBoceto, pero nunca queda guardada
        b.agregar_restriccion("paralela", [l1, 9999])
    assert not b.restricciones


def test_borrar_geometria_con_varias_relaciones_se_lleva_solo_las_suyas():
    b, (l1, l2, l3) = _tres_lineas()
    a = b.agregar_restriccion("horizontal", [l1])
    c = b.agregar_restriccion("paralela", [l1, l2])
    d = b.agregar_restriccion("igual", [l2, l3])
    e = b.agregar_restriccion("vertical", [l3])
    b.eliminar(l2)
    assert set(b.restricciones) == {a, e}                              # paralela e igual dependían de l2
    assert c not in b.restricciones and d not in b.restricciones
    assert resolver(b, {}).ok
    for r in b.restricciones.values():                                 # ninguna referencia huérfana
        assert all(x in b.puntos or x in b.curvas for x in r.entidades)


def test_borrar_un_punto_compartido_no_deja_referencias_rotas():
    b = Boceto()
    j = b.agregar_punto(60, 40)
    l1, l2 = b.agregar_linea((30, 30), j), b.agregar_linea(j, (90, 70))
    b.agregar_restriccion("perpendicular", [l1, l2])
    q = b.agregar_punto(70, 30)
    b.agregar_restriccion("coincidente", [q, l2])
    b.eliminar(j)                                                      # se van las dos líneas y lo que citaba
    assert not b.curvas.keys() & {l1, l2}
    for r in b.restricciones.values():
        assert all(x in b.puntos or x in b.curvas for x in r.entidades)
    assert resolver(b, {}).ok


def test_circulo_sin_radio_no_se_puede_crear_y_linea_de_largo_cero_tampoco():
    b = Boceto()
    with pytest.raises(ErrorBoceto):
        b.agregar_circulo((10, 10), 0)
    p = b.agregar_punto(5, 5)
    with pytest.raises(ErrorBoceto):
        b.agregar_linea(p, p)


def test_tangente_con_la_linea_por_el_centro_no_rompe():
    """La distancia con signo vale 0: configuración límite en la que el signo de la tangencia es ambiguo."""
    b = Boceto()
    k = b.agregar_circulo((60, 40), 12)
    l = b.agregar_linea((20, 40), (100, 40))            # pasa justo por el centro
    b.agregar_restriccion("tangente", [l, k])
    r = resolver(b, {})
    assert r.ok or "conflicto" in r.descripcion().lower()
    if r.ok:
        c, rad = mate_centro(b, k)
        a, d = b.coords(b.curvas[l].p1), b.coords(b.curvas[l].p2)
        assert abs(abs(_dist_recta(c, a, d)) - rad) < TOL


def mate_centro(b, k):
    return _centro_radio(b, k)


# ---------------------------------------------------------------- Restringir automáticamente
def _casi_rectangulo():
    """Cuatro líneas con los extremos compartidos, a 0,4° de ser un rectángulo, más una inclinada a 6° (no debe tocarse)."""
    b = Boceto()
    p = [b.agregar_punto(40, 30), b.agregar_punto(100, 30.3), b.agregar_punto(100.3, 80), b.agregar_punto(40, 80.2)]
    ls = [b.agregar_linea(p[i], p[(i + 1) % 4]) for i in range(4)]
    inclinada = b.agregar_linea((140, 30), (200, 36.3))                  # 6°: fuera de la tolerancia de 1°
    return b, p, ls, inclinada


def test_auto_restringir_solo_agrega_lo_que_la_geometria_cumple():
    from omnicad.restricciones import auto_restringir
    b, p, ls, inclinada = _casi_rectangulo()
    antes = {i: b.coords(i) for i in p}
    agregadas = auto_restringir(b, {}, tipos=["horizontal", "vertical", "paralela", "perpendicular"])
    assert agregadas, "no detectó nada"
    assert resolver(b, {}).ok
    for r in b.restricciones.values():                                     # cada restricción agregada es verdadera
        if r.tipo == "horizontal" and len(r.entidades) == 1:
            c = b.curvas[r.entidades[0]]
            assert abs(b.coords(c.p1)[1] - b.coords(c.p2)[1]) < TOL
        if r.tipo == "vertical" and len(r.entidades) == 1:
            c = b.curvas[r.entidades[0]]
            assert abs(b.coords(c.p1)[0] - b.coords(c.p2)[0]) < TOL
        if r.tipo == "paralela":
            assert abs(_cruz(_dir(b, r.entidades[0]), _dir(b, r.entidades[1]))) < ANG
        if r.tipo == "perpendicular":
            assert abs(_punto(_dir(b, r.entidades[0]), _dir(b, r.entidades[1]))) < ANG
    assert not any(inclinada in r.entidades for r in b.restricciones.values())    # la de 6° queda libre
    assert all(math.dist(antes[i], b.coords(i)) < 0.6 for i in p)                # corrige menos que la tolerancia


def test_auto_restringir_no_duplica_ni_sobredefine():
    from omnicad.restricciones import auto_restringir, restricciones_redundantes
    b, *_ = _casi_rectangulo()
    auto_restringir(b, {})
    valores = {k.id: float(k.expresion) for k in b.cotas.values()}         # las cotas que agregó, con su valor
    gdl = grados_de_libertad(b, valores)
    assert resolver(b, valores).ok
    segunda = auto_restringir(b, valores)                                  # una segunda pasada ya no tiene nada nuevo
    assert segunda == [], segunda
    assert grados_de_libertad(b, valores) == gdl
    assert restricciones_redundantes(b, valores) == []
    pares = [(r.tipo, tuple(sorted(r.entidades))) for r in b.restricciones.values()]
    assert len(pares) == len(set(pares)), "restricciones repetidas"


def test_auto_restringir_por_la_api_se_deshace_en_un_paso():
    s = api.Sesion()

    def L(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, a, r)
        return r["result"]
    L("create_sketch", name="S", plane="XY")
    for x0, y0, x1, y1 in ((40, 30, 100, 30.3), (100, 30.3, 100.3, 80), (100.3, 80, 40, 80.2), (40, 80.2, 40, 30)):
        L("draw_line", sketch="S", start_x=x0, start_y=y0, end_x=x1, end_y=y1)
    antes = L("get_sketch", sketch="S")
    r = L("auto_constrain", sketch="S", types=["horizontal", "vertical", "coincident"])
    assert r["added"]
    despues = L("get_sketch", sketch="S")
    assert despues["dof"] < antes["dof"] and len(despues["constraints"]) > len(antes["constraints"])
    L("undo")
    vuelta = L("get_sketch", sketch="S")
    assert len(vuelta["constraints"]) == len(antes["constraints"]) and vuelta["dof"] == antes["dof"]


def test_un_archivo_con_restricciones_rotas_no_tumba_al_solver():
    """Un .omnicad es un archivo de otro: una restricción que cita un id inexistente o de un tipo que no le corresponde."""
    b, (l1, l2, _l3) = _tres_lineas()
    b.agregar_restriccion("paralela", [l1, l2])
    d = b.a_dict()
    d["restricciones"].append({"id": 900, "tipo": "paralela", "entidades": [l1, 9999], "datos": {}})
    d["restricciones"].append({"id": 901, "tipo": "tangente", "entidades": [l1, l2], "datos": {}})      # dos líneas
    rota = Boceto.desde_dict(d)
    assert len(rota.restricciones) == 1                # las dos rotas se descartan al abrir, como al borrar su geometría
    assert resolver(rota, {}).ok


def test_tangente_linea_arco_se_mide_contra_el_circulo_completo():
    """LIMITACIÓN conocida (docs/seguimiento: BOC-52): la tangencia de una línea con un arco se resuelve contra el
    círculo entero del arco, así que el contacto puede caer fuera del tramo dibujado. Acá el arco va de 0° a 90° y la
    línea queda tangente del lado opuesto (contacto cerca de los 194°)."""
    b = Boceto()
    k = b.agregar_arco_centro((60, 40), (72, 40), (60, 52))
    l = b.agregar_linea((40, 20), (50, 12))
    a, c = b.curvas[l].p1, b.curvas[l].p2
    b.agregar_restriccion("tangente", [l, k])
    assert resolver(b, {}).ok
    centro, radio = _centro_radio(b, k)
    assert abs(abs(_dist_recta(centro, _p(b, a), _p(b, c))) - radio) < TOL     # tangente al círculo completo
    u = _unit(_p(b, a), _p(b, c))
    t = (centro[0] - _p(b, a)[0]) * u[0] + (centro[1] - _p(b, a)[1]) * u[1]
    pie = (_p(b, a)[0] + t * u[0], _p(b, a)[1] + t * u[1])
    ang = math.degrees(math.atan2(pie[1] - centro[1], pie[0] - centro[0])) % 360
    assert not (ang <= 90 or ang >= 360), "si esto empieza a fallar, la limitación se resolvió: borrar BOC-52"



@pytest.mark.parametrize("nombre", list(ESCENARIOS))
def test_guardar_y_reabrir_conserva_la_restriccion_y_el_resultado(nombre):
    b, tipo, ents, _cumple, _mover, _quita = ESCENARIOS[nombre]()
    rid = b.agregar_restriccion(tipo, ents)
    r = resolver(b, {})
    assert r.ok
    otra = Boceto.desde_dict(b.a_dict())                                # lo que se guarda en el .omnicad
    assert otra.restricciones[rid].tipo == tipo and otra.restricciones[rid].entidades == list(ents)
    r2 = resolver(otra, {})
    assert r2.ok and r2.gdl == r.gdl
    assert all(otra.coords(i) == pytest.approx(b.coords(i), abs=TOL) for i in b.puntos)


def test_cambiar_paralela_por_perpendicular_no_colapsa_la_linea():
    """Paralelas exactas son un punto estacionario del residuo de Perpendicular: el solver «cumplía» achicando la línea."""
    b = Boceto()
    l1, l2 = b.agregar_linea((40, 30), (70, 30)), b.agregar_linea((40, 60), (80, 60))
    b.agregar_restriccion("horizontal", [l1])
    rid = b.agregar_restriccion("paralela", [l1, l2])
    assert resolver(b, {}).ok
    b.reemplazar_restriccion(rid, "perpendicular")
    r = resolver(b, {})
    assert r.ok, r.mensaje
    u, v = _unit(*[_p(b, i) for i in b.curvas[l1].extremos()]), _unit(*[_p(b, i) for i in b.curvas[l2].extremos()])
    assert abs(u[0] * v[0] + u[1] * v[1]) < ANG
    assert math.dist(*[_p(b, i) for i in b.curvas[l2].extremos()]) > 10

