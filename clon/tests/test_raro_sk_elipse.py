"""Valores raros en los campos del comando de boceto «sk_elipse» (elipse)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import ANGULO, TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

CENTRO = (20.0, 20.0)
MAYOR = (50.0, 25.0)
MENOR = (25.0, 35.0)

XFAIL_VACIO = pytest.mark.xfail(reason="B-717: el campo vacío se acepta en silencio", strict=True)
XFAIL_ANGULO = pytest.mark.xfail(reason="B-718: el ángulo no frena en 1.000.000°", strict=True)

CASOS = [
    pytest.param("radio_mayor", "", False, id="radio_mayor_vacio", marks=XFAIL_VACIO),
    pytest.param("radio_mayor", "0", False, id="radio_mayor_cero"),
    pytest.param("radio_mayor", "-5", False, id="radio_mayor_negativo"),
    pytest.param("radio_mayor", "2000000", False, id="radio_mayor_enorme"),
    pytest.param("radio_mayor", "20 mm", True, id="radio_mayor_unidad"),
    pytest.param("radio_mayor", "largo", True, id="radio_mayor_expresion"),
    pytest.param("angulo", "", False, id="angulo_vacio", marks=XFAIL_VACIO),
    pytest.param("angulo", "0", True, id="angulo_cero"),
    pytest.param("angulo", "-30", True, id="angulo_negativo"),
    pytest.param("angulo", "2000000", False, id="angulo_enorme", marks=XFAIL_ANGULO),
    pytest.param("angulo", "30 deg", True, id="angulo_unidad"),
    pytest.param("angulo", "giro", True, id="angulo_expresion"),
    pytest.param("radio_menor", "", False, id="radio_menor_vacio", marks=XFAIL_VACIO),
    pytest.param("radio_menor", "0", False, id="radio_menor_cero"),
    pytest.param("radio_menor", "-5", False, id="radio_menor_negativo"),
    pytest.param("radio_menor", "2000000", False, id="radio_menor_enorme"),
    pytest.param("radio_menor", "8 mm", True, id="radio_menor_unidad"),
    pytest.param("radio_menor", "corto", True, id="radio_menor_expresion"),
]


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    tabla = TablaParametros()
    tabla.agregar("largo", "20 mm")
    tabla.agregar("corto", "8 mm")
    tabla.agregar("giro", "30 deg", ANGULO)
    lz = editor_boceto.Lienzo(Boceto(), tabla.evaluar)
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


def _preparar(lz, campo):
    lz.set_herramienta("elipse")
    _clic(lz, *CENTRO)
    _mover(lz, *MAYOR)
    if campo == "radio_menor":
        _clic(lz, *MAYOR)
        _mover(lz, *MENOR)


def _abrir_campo(lz, campo):
    indice = {"radio_mayor": 0, "angulo": 1, "radio_menor": 0}[campo]
    lz._activo = indice
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


def _terminar_elipse(lz):
    elipses = [p for p in lz.b.geometria() if p[0] == "elipse"]
    assert len(elipses) == 1
    _, _, centro, a, b, _ang = elipses[0]
    assert a > 0 and b > 0
    assert lz.resultado.ok
    assert lz.historial


@pytest.mark.parametrize(("campo", "texto", "valido"), CASOS)
def test_valores_raros_de_sk_elipse_no_rompen_el_boceto(lienzo, campo, texto, valido):
    lz = lienzo
    _preparar(lz, campo)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    antes = lz.b.a_dict()

    widget = _abrir_campo(lz, campo)
    entrada = lz.entrada
    _escribir(widget, texto)

    if not valido:
        assert lz.entrada is entrada
        assert lz.b.a_dict() == antes
        assert not lz.historial
        assert lz.resultado.ok
        assert mensajes
        mensaje = mensajes[-1]
        assert "\n" not in mensaje and "\r" not in mensaje
        assert len(mensaje) <= 45
        _escribir(widget, {"radio_mayor": "20", "angulo": "30", "radio_menor": "8"}[campo])
    else:
        assert lz.entrada is None
        assert not mensajes

    if campo in ("radio_mayor", "angulo"):
        _mover(lz, *MENOR)
        _escribir(_abrir_campo(lz, "radio_menor"), "8")
    _terminar_elipse(lz)
