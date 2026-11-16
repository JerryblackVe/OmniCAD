# -*- coding: utf-8 -*-
"""B-595: el marco y las asas de un texto girado giran con él (Fusion), no quedan alineados a los ejes."""
import math

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui.editor_boceto import Lienzo

GIRO = -30.0


def raton(widget, tipo, pos, mods=Qt.NoModifier):
    QApplication.sendEvent(widget, QMouseEvent(tipo, QPointF(pos), widget.mapToGlobal(QPointF(pos)),
        Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
        Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton, mods))


def arrastrar(lz, inicio, fin):
    raton(lz, QEvent.MouseButtonPress, inicio)
    raton(lz, QEvent.MouseMove, fin)
    raton(lz, QEvent.MouseButtonRelease, fin)


def girar(q, grados):
    c, s = math.cos(math.radians(grados)), math.sin(math.radians(grados))
    return (q[0] * c - q[1] * s, q[0] * s + q[1] * c)


@pytest.fixture
def editor():
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    tid = b.agregar_texto((20.0, 20.0), "Hola", 10.0, GIRO, "Arial", False, False)
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(1100, 700)
    lz.ajustar_grilla = lz.objetos.snap = False
    lz.show()
    lz.objetos.registrar_textos()
    app.processEvents()
    lz.seleccion = [lz.objetos.en(lz.a_px(*b.coords(b.curvas[tid].punto)) + QPointF(8, -8)) or tid]
    lz.objetos._firma = None
    yield lz, tid
    lz.close()
    lz.deleteLater()
    app.processEvents()


def test_el_marco_del_texto_gira_con_el_texto(editor):
    lz, tid = editor
    x0, y0, x1, y1, g = lz.objetos.marco()
    assert g == pytest.approx(GIRO)
    ancho, alto = x1 - x0, y1 - y0
    esq = lz.objetos.esquinas_marco()
    assert math.dist(esq[0], esq[1]) == pytest.approx(ancho) and math.dist(esq[1], esq[2]) == pytest.approx(alto)
    # ceñido al texto: bastante menor que la caja de ejes, que es la del bug
    xs, ys = [q[0] for q in esq], [q[1] for q in esq]
    assert ancho * alto < 0.8 * (max(xs) - min(xs)) * (max(ys) - min(ys))
    assert lz.objetos.estado()["ancho"] == pytest.approx(ancho)


def test_las_asas_quedan_sobre_el_rectangulo_girado(editor):
    lz, _tid = editor
    esq, asas = lz.objetos.esquinas_marco(), lz.objetos.manijas()
    for k, q in ((0, esq[0]), (2, esq[1]), (4, esq[2]), (6, esq[3])):
        assert (asas[f"escala{k}"] - lz.a_px(*q)).manhattanLength() < 1e-6
    medio = lz.a_px((esq[0][0] + esq[1][0]) / 2, (esq[0][1] + esq[1][1]) / 2)
    assert (asas["escala1"] - medio).manhattanLength() < 1e-6
    sube = asas["rotar"] - asas["escala5"]           # el asa de giro sale hacia afuera del lado de arriba
    ejes = lz.a_px(*girar((0, 1), GIRO)) - lz.a_px(0, 0)
    assert sube.x() * ejes.x() + sube.y() * ejes.y() > 0


def test_escalar_por_un_lado_estira_solo_el_ancho_del_texto(editor):
    lz, _tid = editor
    for o in lz.b.objetos.values():
        o["proporciones"] = False
    ancho, alto = (lambda m: (m[2] - m[0], m[3] - m[1]))(lz.objetos.marco())
    asa = lz.objetos.manijas()["escala3"]          # el medio del lado derecho
    paso = np.array(girar((10.0, 0.0), GIRO))      # 10 mm a lo largo del texto
    arrastrar(lz, asa, lz.a_px(*(np.asarray(lz.a_mm(asa)) + paso)))
    nuevo = lz.objetos.marco()
    assert nuevo[4] == pytest.approx(GIRO)
    assert nuevo[2] - nuevo[0] == pytest.approx(ancho + 10, rel=1e-3)
    assert nuevo[3] - nuevo[1] == pytest.approx(alto, rel=1e-3)


def test_un_clic_fuera_del_rectangulo_girado_no_elige_el_texto(editor):
    lz, _tid = editor
    esq = lz.objetos.esquinas_marco()
    lz.seleccion = []
    lz.objetos._firma = None
    caja_ejes = (min(q[0] for q in esq), min(q[1] for q in esq), max(q[0] for q in esq), max(q[1] for q in esq))
    afuera = lz.a_px(caja_ejes[0] + 0.5, caja_ejes[3] - 0.5)     # esquina de la caja de ejes: fuera del rectángulo
    assert lz.objetos.en(afuera) is None
    dentro = lz.a_px(*np.mean(esq, axis=0))
    assert lz.objetos.en(dentro) is not None


def test_el_cuadro_de_trazos_al_escribir_gira_con_el_texto(editor):
    lz, _tid = editor
    lz._previa_texto = {"caja": (0.0, 0.0, 40.0, 10.0), "angulo": 90.0}   # cuadro dibujado, texto girado 90°
    esq = lz._cuadro_texto_previa()
    assert esq[3] == pytest.approx((0.0, 10.0))                         # gira alrededor de su esquina de arriba a la izquierda
    assert esq[1] == pytest.approx((10.0, 50.0))
    lz._previa_texto = {"caja": None, "angulo": 30.0}
    lz._previa_polis = [[(q[0] * math.cos(math.radians(30)) - q[1] * math.sin(math.radians(30)),
                          q[0] * math.sin(math.radians(30)) + q[1] * math.cos(math.radians(30)))
                         for q in ((0.0, 0.0), (20.0, 0.0), (20.0, 5.0), (0.0, 5.0))]]     # letras de 20 × 5 escritas a 30°
    esq = lz._cuadro_texto_previa()
    assert sorted((math.dist(esq[0], esq[1]), math.dist(esq[1], esq[2]))) == pytest.approx([5.0, 20.0])
    lz._previa_texto, lz._previa_polis = None, []


def test_marco_generico_de_un_texto_con_restricciones_tambien_gira():
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    tid = b.agregar_texto((20.0, 20.0), "Hola", 10.0, GIRO, "Arial", False, False)
    linea = b.agregar_linea((0.0, 0.0), (20.0, 20.0))
    b.agregar_restriccion("coincidente", [b.curvas[tid].punto, b.curvas[linea].p2])   # lo ata a otra geometría
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(1100, 700)
    lz.show()
    lz.objetos.registrar_textos()
    app.processEvents()
    assert not lz.objetos.seleccion()                    # sin objeto vectorial: manda el marco genérico
    lz.seleccion = [tid]
    lz.mostrar_marco, lz.herramienta, lz.fase = True, "seleccionar", None
    assert lz._giro_marco() == pytest.approx(GIRO)
    caja = lz._caja_marco()
    esq = lz._esquinas_marco(caja, GIRO)
    asas = lz._manijas_marco(caja)
    assert (asas["escala0"] - lz.a_px(*esq[0])).manhattanLength() < 1e-6
    assert (asas["escala2"] - lz.a_px(*esq[2])).manhattanLength() < 1e-6
    assert math.dist(esq[0], esq[1]) == pytest.approx(caja[2] - caja[0])
    sube = asas["rotar"] - lz.a_px((esq[2][0] + esq[3][0]) / 2, (esq[2][1] + esq[3][1]) / 2)
    ejes = lz.a_px(*girar((0, 1), GIRO)) - lz.a_px(0, 0)
    assert sube.x() * ejes.x() + sube.y() * ejes.y() > 0
    lz.close()
    lz.deleteLater()


def test_b597_un_objeto_girado_con_la_matriz_tambien_tiene_el_marco_girado():
    from omnicad.restricciones import objetos as ob
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    oid = ob.crear(b, b.agregar_rectangulo((10, 10), (50, 30)), "Logo")      # 40 × 20
    ob.transformar(b, [oid], ob.afin(angulo=30, pivote=(30, 20)))
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(1100, 700)
    lz.show()
    app.processEvents()
    lz.seleccion = [oid]
    x0, y0, x1, y1, g = lz.objetos.marco()
    assert g == pytest.approx(30)
    assert (x1 - x0, y1 - y0) == pytest.approx((40, 20), abs=0.05)           # ceñido al rectángulo girado, no a su caja de ejes
    assert lz.objetos.estado()["ancho"] == pytest.approx(40, abs=0.05)
    lz.close()
    lz.deleteLater()
