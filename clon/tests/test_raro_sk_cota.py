# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_cota»: la barra de entrada de la cota con cada valor raro
(vacío, cero, negativo, enorme, con unidades, con expresión). Los inválidos se rechazan con un mensaje de un solo
renglón y no cierran la barra ni dejan el boceto roto; los válidos crean la cota y cierran la barra."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto, resolver
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import editor_boceto


# (valor tipeado, ¿la barra queda abierta porque se rechazó?)
CASOS = [
    ("", False),
    ("0", True),
    ("-5", True),
    ("1e9", True),
    ("5mm", False),
    ("5*2", False),
]


@pytest.fixture
def lz():
    app = QApplication.instance() or QApplication([])
    lienzo = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lienzo.resize(800, 600)
    lienzo.ajustar_grilla = False
    lienzo.show()
    lienzo.mensajes = []
    lienzo.mensaje.connect(lienzo.mensajes.append)
    yield lienzo
    lienzo.close()
    lienzo.deleteLater()
    app.processEvents()


def _clic(lz, x, y):
    pos = lz.a_px(x, y)
    for tipo, boton, botones in ((QEvent.MouseMove, Qt.NoButton, Qt.NoButton),
                                 (QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton),
                                 (QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, boton, botones, Qt.NoModifier))


@pytest.mark.parametrize("valor,queda_abierta", CASOS)
def test_raro_sk_cota(lz, valor, queda_abierta):
    lz.set_herramienta("punto")
    _clic(lz, 30, 20)
    punto = max(lz.b.puntos)
    lz.set_herramienta("cota")
    for xy in ((30, 20), (0, 0)):
        _clic(lz, *xy)
    assert set(lz.picks) == {punto, Boceto.ORIGEN}
    assert lz._esperando_ubicacion
    _clic(lz, 15, 40)
    assert lz.entrada is not None

    campo = lz.entrada.campos[0]
    campo.setText(valor)
    QTest.keyClick(campo, Qt.Key_Return)
    QApplication.instance().processEvents()

    assert (lz.entrada is not None) == queda_abierta, (valor, lz.entrada is not None)
    for m in lz.mensajes:
        assert "\n" not in m
    try:
        resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed after value {valor!r}: {e}")

    if lz.entrada is not None:
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()
