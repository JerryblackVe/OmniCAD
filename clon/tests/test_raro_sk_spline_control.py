# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_spline_control».

La spline de puntos de control no abre una caja de diálogo con campos editables: se define por clics y se
termina con Enter o doble clic; el único ajuste es el Grado (3 o 5) de la tarjeta. Por eso no hay campos que
probar con vacío, 0, negativo, enorme, unidades o expresión; este archivo deja pruebas de humo que crean una
spline de puntos de control abierta y una cerrada, con los dos grados, y verifican que no rompen el boceto
ni la aplicación. Mensajes de un renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

app_qt = None


@pytest.fixture
def lienzo():
    global app_qt
    app = QApplication.instance() or QApplication([])
    app_qt = app
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _mover(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _clic(lz, x, y):
    _mover(lz, x, y)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


@pytest.mark.parametrize("grado", [3, 5])
def test_valores_raros_de_sk_spline_control_no_rompen_el_boceto(lienzo, grado):
    lz = lienzo
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.opciones["grado_spline"] = grado
    lz.set_herramienta("spline_control")
    for xy in ((0, 0), (10, 6), (20, -3), (30, 4)):
        _clic(lz, *xy)
    sid = lz._terminar_spline()
    assert sid is not None
    assert lz.resultado.ok
    assert all("\n" not in m and "\r" not in m for m in mensajes)
    try:
        resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed: {e}")
    assert lz.isVisible()
    assert QApplication.instance() is not None

    # cerrada
    lz2 = None
    try:
        lz2 = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
        lz2.resize(800, 600)
        lz2.ajustar_grilla = False
        lz2.show()
        lz2.opciones["grado_spline"] = grado
        lz2.set_herramienta("spline_control")
        for xy in ((50, 0), (60, 10), (70, 0), (60, -8), (50, 0)):
            _clic(lz2, *xy)
        sid2 = lz2._terminar_spline(cerrar=True)
        assert sid2 is not None
        assert lz2.resultado.ok
        try:
            resolver(lz2.b)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"resolver crashed (cerrada): {e}")
    finally:
        if lz2 is not None:
            lz2.close()
            lz2.deleteLater()
            QApplication.instance().processEvents()
