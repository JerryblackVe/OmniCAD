# -*- coding: utf-8 -*-
"""PRUEBA-ASAS: arrastrar las asas de Escala, Mover/copiar y Texto del boceto a posiciones raras (sobre la base, lejísimos,
NaN, infinito, vueltas completas): la caja siempre queda con un número finito y dentro del tope del asa."""
import math
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QLineEdit

from omnicad.ui import asas_boceto as ab


class _Lienzo:
    """Lo mínimo del lienzo que usa el gestor: 1 px = 1 mm. `b`: un boceto real si se lo pasa."""
    _desfase_modo, _desfase_invertido = "un", False

    def __init__(self, polis, b=None):
        self._polis = polis
        self.b = b or SimpleNamespace(objetos={}, curvas={"c": 1}, puntos={})

    def px_por_mm(self):
        return 1.0

    def evaluar(self, texto, _tipo):
        return float(texto.replace(",", "."))

    def a_mm(self, p):
        return (p.x(), p.y())

    def a_px(self, x, y):
        return QPointF(x, y)

    def _polilineas(self, _c):
        return self._polis

    def update(self):
        pass

    def setCursor(self, *_a):
        pass

    def unsetCursor(self):
        pass


def _gestor(construir, textos, base=(0.0, 0.0)):
    QApplication.instance() or QApplication([])
    l = _Lienzo([[(0.0, 0.0), (40.0, 0.0), (40.0, 20.0)]])
    asas, tipos, _p = construir(l, base)
    cajas = [QLineEdit(t) for t in textos]
    return ab.GestorAsas2D(l, SimpleNamespace(campos=cajas), asas, tipos), cajas


RAROS = [(0.0, 0.0), (1e-9, 0.0), (-500.0, -500.0), (1e12, 1e12), (float("nan"), 3.0), (float("inf"), 0.0), (-1e300, 1e300)]


@pytest.mark.parametrize("xy", RAROS)
def test_escala_asa_factor_siempre_finito_y_con_tope(xy):
    g, cajas = _gestor(lambda l, b: ab.asas_escala(l, ["c"], b), ["1"])
    assert g.empezar(g.posiciones_px()[0][1])
    g.mover(QPointF(*xy))
    g.soltar()
    f = float(cajas[0].text().replace(",", "."))
    assert math.isfinite(f) and f >= 1e-3


@pytest.mark.parametrize("xy", RAROS)
def test_mover_asas_siempre_finitas(xy):
    for i in (0, 1):
        g, cajas = _gestor(lambda l, b: ab.asas_mover(l, ["c"], b), ["0", "0", "0"])
        assert g.empezar(g.posiciones_px()[i][1])
        g.mover(QPointF(*xy))
        g.soltar()
        assert all(math.isfinite(float(c.text().replace(",", "."))) for c in cajas)


def test_texto_giro_da_vueltas_completas_sin_saltar():
    g, cajas = _gestor(lambda l, b: ab.asas_texto(l, b, 30.0), ["x", "5", "0", "1", "1"])
    assert g.empezar(g.posiciones_px()[0][1])
    g.mover(QPointF(0.0, 30.0))
    assert abs(float(cajas[2].text().replace(",", ".")) - 90.0) < 0.01
    g.mover(QPointF(-30.0, 0.0))
    assert abs(abs(float(cajas[2].text().replace(",", "."))) - 180.0) < 0.01
    g.mover(QPointF(float("nan"), 0.0))                     # NaN: no toca la caja
    assert abs(abs(float(cajas[2].text().replace(",", "."))) - 180.0) < 0.01


def _esquina():
    """Boceto real con una L: líneas (0,0)-(50,0) y (0,0)-(0,50)."""
    from omnicad.restricciones.boceto import Boceto
    b = Boceto()
    return b, b.agregar_linea((0, 0), (50, 0)), b.agregar_linea((0, 0), (0, 50))


def _gestor_real(construir, textos):
    QApplication.instance() or QApplication([])
    b, l1, l2 = _esquina()
    l = _Lienzo([[(0.0, 0.0), (50.0, 0.0)]], b)
    asas, tipos, previa = construir(l, [l1, l2], [(25.0, 0.0), (0.0, 25.0)])
    return ab.GestorAsas2D(l, SimpleNamespace(campos=[QLineEdit(t) for t in textos]), asas, tipos, previa)


CASOS_REALES = [
    ("empalme", lambda l, p, x: ab.asas_empalme(l, p, x), ["5"], 1e-3),
    ("chaflan", lambda l, p, x: ab.asas_chaflan(l, "chaflan", p, x), ["5"], 1e-3),
    ("chaflan_dos_dist", lambda l, p, x: ab.asas_chaflan(l, "chaflan_dos_dist", p, x), ["5", "7"], 1e-3),
    ("chaflan_dist_angulo", lambda l, p, x: ab.asas_chaflan(l, "chaflan_dist_angulo", p, x), ["5", "30"], 1e-3),
]


@pytest.mark.parametrize("xy", RAROS)
@pytest.mark.parametrize(("nombre", "construir", "textos", "minimo"), CASOS_REALES)
def test_empalme_y_chaflan_asas_siempre_finitas(nombre, construir, textos, minimo, xy):
    for i in range(len(textos)):
        g = _gestor_real(construir, textos)             # un gestor por asa: con la otra en 1e12 el chaflán ya no entra
        q = g.posiciones_px()[i][1]
        assert q is not None, f"{nombre}: el asa {i} no tiene posición con valores válidos"
        assert g.empezar(q)
        g.mover(QPointF(*xy))
        g.soltar()
        valores = g.valores()
        assert all(math.isfinite(x) for x in valores), (nombre, valores)
        assert valores[0] >= minimo


@pytest.mark.parametrize("modo", ["un", "dos", "simetrico"])
@pytest.mark.parametrize("invertido", [False, True])
@pytest.mark.parametrize("xy", RAROS)
def test_desfase_asa_finita_y_simetrico_positivo(modo, invertido, xy):
    QApplication.instance() or QApplication([])
    l = _Lienzo([[(0.0, 0.0), (50.0, 0.0)]])
    l._desfase_modo, l._desfase_invertido = modo, invertido
    asas, tipos, _p = ab.asas_desfase(l, ((10.0, 0.0), (0.0, 1.0)))
    g = ab.GestorAsas2D(l, SimpleNamespace(campos=[QLineEdit("5") for _ in tipos]), asas, tipos)
    for i in range(len(asas)):
        assert g.empezar(g.posiciones_px()[i][1])
        g.mover(QPointF(*xy))
        g.soltar()
    valores = g.valores()
    assert all(math.isfinite(x) for x in valores)
    if modo == "simetrico":
        assert all(x >= 0 for x in valores)


def test_desfase_sin_normal_no_tiene_asas():
    assert ab.asas_desfase(_Lienzo([]), None) is None
