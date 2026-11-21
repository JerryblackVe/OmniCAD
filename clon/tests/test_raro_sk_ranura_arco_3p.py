"""Valores raros en los campos del comando de boceto «sk_ranura_arco_3p» (ranura de arco de tres puntos)."""
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

CENTRO1 = (-10.0, 0.0)
CENTRO2 = (10.0, 0.0)
PUNTO_ARCO = (0.0, 10.0)
CURSOR_ANCHO = (0.0, 12.0)


CASOS = [
    pytest.param("ancho", "", True, id="ancho_vacio"),
    pytest.param("ancho", "0", False, id="ancho_cero"),
    pytest.param("ancho", "-5", False, id="ancho_negativo"),
    pytest.param("ancho", "2000000", False, id="ancho_enorme"),
    pytest.param("ancho", "5 mm", True, id="ancho_unidad"),
    pytest.param("ancho", "2*3", True, id="ancho_expresion"),
]


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
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


def _preparar(lz):
    lz.set_herramienta("ranura_arco_3p")
    _clic(lz, *CENTRO1)
    _clic(lz, *CENTRO2)
    _clic(lz, *PUNTO_ARCO)
    _mover(lz, *CURSOR_ANCHO)


def _abrir_campo(lz):
    lz._activo = 0
    lz._editar_campo_vivo("0")
    assert lz.entrada is not None
    return lz.entrada.campos[0]


def _escribir(campo, texto):
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(campo, texto)
    else:
        QTest.keyClick(campo, Qt.Key_Backspace)
    QTest.keyClick(campo, Qt.Key_Return)


def _ranuras(lz):
    return [c for c in lz.b.curvas.values() if c.tipo in ("linea", "arco")]


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS)
def test_valores_raros_de_sk_ranura_arco_3p_no_rompen_el_boceto(lienzo, campo, texto, valido):
    lz = lienzo
    _preparar(lz)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    antes = lz.b.a_dict()

    widget = _abrir_campo(lz)
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
        assert lz.b.a_dict() == antes, (campo, texto)
        assert not lz.historial
        assert lz.resultado.ok
        assert mensajes, (campo, texto)
        mensaje = mensajes[-1]
        assert "\\n" not in mensaje and "\\r" not in mensaje, mensaje
        assert len(mensaje) <= 80, mensaje
        _escribir(widget, "5")
        QApplication.instance().processEvents()
    else:
        assert lz.entrada is None, (campo, texto)
        assert not mensajes
        assert lz.b.a_dict() != antes, (campo, texto)

    if lz.entrada is not None:
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()
    assert lz.resultado.ok
    assert resolver(lz.b).ok
    assert lz.historial
    assert lz.isVisible()
