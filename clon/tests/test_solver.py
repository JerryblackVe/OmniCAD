# -*- coding: utf-8 -*-
import math

import pytest

from omnicad.restricciones import Boceto, ErrorBoceto, grados_de_libertad, resolver
from omnicad.restricciones.boceto import distancia_punto_recta


def _rect_acotado(ancho=50, alto=25):
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (30, 20))
    esquina = b.curvas[lineas[0]].p1
    b.agregar_restriccion("fijo", [esquina])
    c1 = b.agregar_cota("distancia", [lineas[0]], str(ancho))
    c2 = b.agregar_cota("distancia", [lineas[1]], str(alto))
    return b, lineas, {c1: ancho, c2: alto}


def test_rectangulo_libre_tiene_4_gdl():
    b = Boceto()
    b.agregar_rectangulo((0, 0), (30, 20))
    assert grados_de_libertad(b) == 4          # posición (2) + ancho + alto


def test_rectangulo_totalmente_restringido():
    b, lineas, valores = _rect_acotado()
    r = resolver(b, valores)
    assert r.ok and r.totalmente_restringido
    xs = sorted(round(p.x, 6) for p in b.puntos.values())
    ys = sorted(round(p.y, 6) for p in b.puntos.values())
    assert xs == [0, 0, 50, 50] and ys == [0, 0, 25, 25]


def test_cambio_de_cota_mueve_geometria():
    b, lineas, valores = _rect_acotado()
    resolver(b, valores)
    valores = {k: (80 if v == 50 else v) for k, v in valores.items()}
    assert resolver(b, valores).ok
    assert b.medir_cota("distancia", [lineas[0]]) == pytest.approx(80, abs=1e-6)


@pytest.mark.parametrize("tipo,construir,verificar", [
    ("paralela", lambda b: [b.agregar_linea((0, 0), (10, 1)), b.agregar_linea((0, 5), (10, 8))],
     lambda b, e: abs(b._direccion(e[0])[0] * b._direccion(e[1])[1] - b._direccion(e[0])[1] * b._direccion(e[1])[0])),
    ("perpendicular", lambda b: [b.agregar_linea((0, 0), (10, 1)), b.agregar_linea((0, 0.5), (1, 8))],
     lambda b, e: abs(sum(a * c for a, c in zip(b._direccion(e[0]), b._direccion(e[1]), strict=True)))),
    ("igual", lambda b: [b.agregar_linea((0, 0), (10, 0)), b.agregar_linea((0, 5), (4, 5))],
     lambda b, e: abs(b.medir_cota("distancia", [e[0]]) - b.medir_cota("distancia", [e[1]]))),
    ("concentrica", lambda b: [b.agregar_circulo((0, 0), 5), b.agregar_circulo((1, 2), 2)],
     lambda b, e: math.dist(b.coords(b.curvas[e[0]].centro), b.coords(b.curvas[e[1]].centro))),
    ("tangente", lambda b: [b.agregar_linea((-10, 0), (10, 0)), b.agregar_circulo((0, 4), 3)],
     lambda b, e: abs(abs(distancia_punto_recta(b.coords(b.curvas[e[1]].centro), *b._extremos_linea(e[0])))
                      - b.curvas[e[1]].radio)),
])
def test_restricciones_se_cumplen(tipo, construir, verificar):
    b = Boceto()
    e = construir(b)
    b.agregar_restriccion(tipo, e)
    assert resolver(b).ok
    assert verificar(b, e) < 1e-6


def test_horizontal_vertical_coincidente_punto_medio():
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (10, 2))
    l2 = b.agregar_linea((3, 3), (4, 9))
    p = b.agregar_punto(7, 7)
    b.agregar_restriccion("horizontal", [l1])
    b.agregar_restriccion("vertical", [l2])
    b.agregar_restriccion("punto_medio", [p, l1])
    b.agregar_restriccion("coincidente", [b.curvas[l2].p1, l1])
    assert resolver(b).ok
    (x1, y1), (x2, y2) = b._extremos_linea(l1)
    assert abs(y1 - y2) < 1e-6
    (a, _), (c, _) = b._extremos_linea(l2)
    assert abs(a - c) < 1e-6
    assert b.coords(p) == pytest.approx(((x1 + x2) / 2, (y1 + y2) / 2), abs=1e-6)


def test_cotas_radio_diametro_angulo():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 3)
    a = b.agregar_arco_3_puntos((10, 0), (14, 4), (18, 0))
    l1 = b.agregar_linea((0, 20), (10, 20))
    l2 = b.agregar_linea((0, 20), (5, 28))
    k1 = b.agregar_cota("radio", [c], "7")
    k2 = b.agregar_cota("diametro", [a], "20")
    k3 = b.agregar_cota("angulo", [l1, l2], "30")
    assert resolver(b, {k1: 7, k2: 20, k3: 30}).ok
    assert b.radio(c) == pytest.approx(7, abs=1e-6)
    assert b.radio(a) == pytest.approx(10, abs=1e-6)
    assert b.medir_cota("angulo", [l1, l2]) == pytest.approx(30, abs=1e-5)


def test_conflicto_se_detecta():
    b, lineas, valores = _rect_acotado()
    b.agregar_restriccion("horizontal", [lineas[1]])   # un lado vertical no puede ser horizontal
    r = resolver(b, valores)
    assert not r.ok and r.estado == "inconsistente"


def test_colapso_a_largo_cero_es_conflicto():
    """'Horizontal' sobre un lado vertical se cumpliría achicándolo a cero: debe contar como conflicto."""
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (30, 20))
    c = b.agregar_cota("distancia", [lineas[0]], "60")
    b.agregar_restriccion("horizontal", [lineas[1]])
    r = resolver(b, {c: 60})
    assert not r.ok and "colapsa" in r.mensaje


def test_validaciones_de_tipo():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 3)
    with pytest.raises(ErrorBoceto):
        b.agregar_restriccion("horizontal", [c])
    with pytest.raises(ErrorBoceto):
        b.agregar_cota("radio", [b.curvas[c].centro], "3")
    with pytest.raises(ErrorBoceto):
        b.agregar_arco_3_puntos((0, 0), (1, 1), (2, 2))   # alineados


def test_eliminar_en_cascada_y_serializar():
    b, lineas, _ = _rect_acotado()
    n_restr = len(b.restricciones)
    b.eliminar(lineas[0])
    assert lineas[0] not in b.curvas
    assert len(b.restricciones) < n_restr          # se fue la horizontal de esa línea
    b2 = Boceto.desde_dict(b.a_dict())
    assert b2.a_dict() == b.a_dict()
    nuevo = b2.agregar_punto(1, 1)
    assert nuevo not in b.puntos or nuevo > max(b.puntos)   # los ids nuevos no chocan


def test_tangencia_con_extremo_compartido_no_cuenta_grados_de_libertad_de_mas():
    """Línea fija + arco tangente que nace en su extremo + radio + fin a la altura del centro: GDL 0.
    (Con "distancia del centro a la recta = radio" el jacobiano es singular en el punto de tangencia.)"""
    b = Boceto()
    ln = b.agregar_linea((0, 0), (10, 0))
    b.agregar_restriccion("fijo", [ln])
    arco = b.agregar_arco_centro((10, 5), b.curvas[ln].p2, (15, 5))
    b.agregar_restriccion("tangente", [ln, arco])
    b.agregar_restriccion("horizontal", [b.curvas[arco].centro, b.curvas[arco].fin])
    k = b.agregar_cota("radio", [arco], "5")
    r = resolver(b, {k: 5})
    assert r.ok and r.gdl == 0
    assert b.coords(b.curvas[arco].centro) == pytest.approx((10, 5))
