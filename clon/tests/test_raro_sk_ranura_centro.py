# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_ranura_centro»: los campos Largo, Ángulo y Ancho de su caja en vacío, 0,
negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y todo aviso es
de un renglón."""
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
    ("largo", "", True),
    ("largo", "0", False),
    ("largo", "-5", False),
    ("largo", "2000000", False),
    ("largo", "20 mm", True),
    ("largo", "30 deg", False),
    ("largo", "5*2", True),
    ("angulo", "", True),
    ("angulo", "0", True),
    ("angulo", "-5", True),
    ("angulo", "2000000", False),
    ("angulo", "30 deg", True),
    ("angulo", "20 mm", False),
    ("angulo", "5*2", True),
    ("ancho", "", True),
    ("ancho", "0", False),
    ("ancho", "-5", False),
    ("ancho", "2000000", False),
    ("ancho", "6 mm", True),
    ("ancho", "30 deg", False),
    ("ancho", "5*2", True),
]


def _preparar(lz, campo):
    lz.set_herramienta("ranura_centro")
    if campo in ("largo", "angulo"):
        _clic(lz, 0, 0)
        _mover(lz, 20, 0)
    else:
        _clic(lz, 0, 0)
        _mover(lz, 20, 0)
        _clic(lz, 20, 0)
        _mover(lz, 10, 3)


def _abrir_campo(lz, campo):
    indice = {"largo": 0, "angulo": 1, "ancho": 0}[campo]
    lz._activo = indice
    lz._editar_campo_vivo("0")
    assert lz.entrada is not None, campo
    return lz.entrada.campos[0]


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS, ids=[f"{c}_{t or 'vacio'}" for c, t, _ in CASOS])
def test_valores_raros_de_sk_ranura_centro_no_rompen_el_boceto(lienzo, campo, texto, valido):
    lz = lienzo
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    _preparar(lz, campo)
    antes = lz.b.a_dict()
    mensajes.clear()

    widget = _abrir_campo(lz, campo)
    entrada = lz.entrada
    _escribir(widget, texto)
    QApplication.instance().processEvents()

    assert QApplication.instance() is not None
    assert lz.isVisible()

    try:
        resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed after {campo}={texto!r}: {e}")

    if not valido:
        assert lz.entrada is entrada, (campo, texto)
        assert lz.b.a_dict() == antes, (campo, texto)
        assert mensajes, (campo, texto)
        mensaje = mensajes[-1]
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje
        assert len(mensaje) <= 80, mensaje
        _escribir(widget, "20" if campo == "largo" else ("30" if campo == "angulo" else "6"))
    else:
        assert lz.entrada is None, (campo, texto)
        assert not [m for m in mensajes if "\n" in m or "\r" in m], mensajes

    if lz.entrada is not None:
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()
