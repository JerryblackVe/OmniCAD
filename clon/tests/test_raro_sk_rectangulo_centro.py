# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_rectangulo_centro»: los campos Ancho y Alto de su caja en vacío, 0,
negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y todo aviso
es de un renglón."""
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


def _escribir(widget, texto):
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(widget, texto)
    else:
        QTest.keyClick(widget, Qt.Key_Backspace)
    QTest.keyClick(widget, Qt.Key_Return)


CASOS = [
    ("ancho", "", True),
    ("ancho", "0", False),
    ("ancho", "-5", False),
    ("ancho", "2000000", False),
    ("ancho", "20 mm", True),
    ("ancho", "5*2", True),
    ("alto", "", True),
    ("alto", "0", False),
    ("alto", "-5", False),
    ("alto", "2000000", False),
    ("alto", "10 mm", True),
    ("alto", "5*2", True),
]


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS, ids=[f"{c}_{t or 'vacio'}" for c, t, _ in CASOS])
def test_valores_raros_de_sk_rectangulo_centro_no_rompen_el_boceto(lienzo, campo, texto, valido):
    lz = lienzo
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.set_herramienta("rectangulo_centro")
    _clic(lz, 0, 0)
    _mover(lz, 10, 5)
    antes = len(lz.b.curvas)
    lz._activo = 0 if campo == "ancho" else 1
    lz._editar_campo_vivo("0")
    assert lz.entrada is not None
    widget = lz.entrada.campos[0]
    entrada = lz.entrada
    _escribir(widget, texto)
    QApplication.instance().processEvents()

    assert QApplication.instance() is not None
    assert lz.isVisible()
    try:
        resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed after value {texto!r}: {e}")

    if not valido:
        assert lz.entrada is entrada, (campo, texto)
        assert len(lz.b.curvas) == antes, (campo, texto)
        assert mensajes, (campo, texto)
        mensaje = mensajes[-1]
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje
        assert len(mensaje) <= 80, mensaje
        _escribir(widget, "20" if campo == "ancho" else "10")
        QApplication.instance().processEvents()
    else:
        assert lz.entrada is None, (campo, texto)
        assert not [m for m in mensajes if "mayor que 0" in m or "máximo" in m or "entre 0 y" in m], mensajes
        assert len(lz.b.curvas) >= antes, (campo, texto)

    if lz.entrada is not None:
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()
