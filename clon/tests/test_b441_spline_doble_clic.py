"""B-441: terminar splines con ratón simulado, sin repetir el punto final."""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui.editor_boceto import Lienzo


@pytest.fixture(params=["spline_ajuste", "spline_control"])
def lienzo(request):
    app = QApplication.instance() or QApplication([])
    lz = Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XY"))
    lz.ajustar_grilla = False
    lz.resize(800, 600)
    lz.show()
    lz.set_herramienta(request.param)
    app.processEvents()
    yield lz
    lz.close()
    lz.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)


def _evento(lz, tipo, pos):
    botones = Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, pos, QPointF(lz.mapToGlobal(pos.toPoint())),
                                         Qt.LeftButton, botones, Qt.NoModifier))


def _clic(lz, punto, doble=False):
    pos = lz.a_px(*punto)
    tipos = [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]
    if doble:
        # Qt reemplaza la segunda presión por DblClick; la segunda liberación sí llega.
        tipos += [QEvent.MouseButtonDblClick, QEvent.MouseButtonRelease]
    for tipo in tipos:
        _evento(lz, tipo, pos)


def _comprobar_spline(lz, puntos):
    splines = [c for c in lz.b.curvas.values() if c.tipo == "spline"]
    assert len(splines) == 1, "el doble clic debe dejar una spline creada"
    spline = splines[0]
    assert len(spline.pts) == len(puntos), "el punto final debe agregarse una sola vez"
    for pid, esperado in zip(spline.pts, puntos, strict=True):
        assert lz.b.coords(pid) == pytest.approx(esperado)
    assert not lz.clics, "la segunda liberación no debe empezar otra spline"
    assert lz.entrada is None
    assert lz.resultado.ok


@pytest.mark.parametrize("cantidad", [2, 4])
def test_doble_clic_agrega_el_ultimo_punto_una_vez(lienzo, cantidad):
    puntos = [(10, 15), (25, 30), (40, 10), (55, 25)][:cantidad]
    for punto in puntos[:-1]:
        _clic(lienzo, punto)
    assert not lienzo.b.curvas
    _clic(lienzo, puntos[-1], doble=True)
    _comprobar_spline(lienzo, puntos)
    assert len(lienzo.historial) == 1


def test_doble_clic_sobre_una_cota_termina_la_spline(lienzo):
    """La edición de una cota no debe robar el gesto de la herramienta activa."""
    b = lienzo.b
    linea = b.agregar_linea((-60, -30), (-40, -30))
    cota = b.agregar_cota("distancia", [linea], "20")
    lienzo.resolver()
    lienzo.repaint()
    pos = lienzo._zonas_cotas[cota].center()
    puntos = [(10, 15), (25, 30), (40, 10), lienzo.a_mm(pos)]
    for punto in puntos[:-1]:
        _clic(lienzo, punto)
    _clic(lienzo, puntos[-1], doble=True)
    _comprobar_spline(lienzo, puntos)
    assert b.cotas[cota].expresion == "20"


@pytest.mark.parametrize("tecla", [Qt.Key_Return, Qt.Key_Enter])
def test_enter_sigue_terminando_la_spline(lienzo, tecla):
    puntos = [(10, 15), (25, 30), (40, 10), (55, 25)]
    for punto in puntos:
        _clic(lienzo, punto)
    assert not lienzo.b.curvas
    QTest.keyClick(lienzo, tecla)
    _comprobar_spline(lienzo, puntos)
