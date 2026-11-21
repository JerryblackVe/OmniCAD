# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_circulo_2p» (círculo de 2 puntos): el campo Diámetro de su barra en
vacío, 0, negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y
todo aviso es de un renglón. La ayuda de Fusion (`create circles in a sketch`, docs/fusion_docs/contenido/
fusion-sketch/create-circles-in-a-sketch-e87fd277002.md) manda un primer clic y escribir el diámetro o dar el
segundo punto; el rechazo de 0 y negativos y el tope de 1 km vienen de `validar_valor_cota`, como en las otras
cotas."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

PRIMERO = (0.0, 0.0)
RATON = (30.0, 0.0)                      # diámetro de 30 mm si no se escribe nada

CASOS = [
    ("", 15.0),                          # sin diámetro: lo dan los dos puntos del ratón, como Fusion
    ("0", None),
    ("-5", None),
    ("2000000", None),                   # por encima del tope de 1 km
    ("50 mm", 25.0),
    ("mi_diametro", 25.0),               # parámetro del documento = 50 mm
]


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    tabla = TablaParametros()
    tabla.agregar("mi_diametro", "50 mm")
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


def _escribir(widget, texto):
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(widget, texto)
    else:
        QTest.keyClick(widget, Qt.Key_Backspace)
    QTest.keyClick(widget, Qt.Key_Return)


def _circulos(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "circulo"]


@pytest.mark.parametrize(("texto", "radio"), CASOS, ids=[t or "vacio" for t, _ in CASOS])
def test_valores_raros_de_sk_circulo_2p_no_rompen_el_boceto(lienzo, texto, radio):
    lz = lienzo
    lz.set_herramienta("circulo_2p")
    _clic(lz, *PRIMERO)
    _mover(lz, *RATON)
    assert lz._claves_vivas() == ["diametro"]   # un solo campo en la barra de esta herramienta
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    antes = lz.b.a_dict()

    lz._editar_campo_vivo("0")           # abre el campo Diámetro de la caja flotante
    assert lz.entrada is not None
    campo = lz.entrada.campos[0]
    entrada = lz.entrada
    _escribir(campo, texto)
    QApplication.instance().processEvents()

    assert QApplication.instance() is not None and lz.isVisible()
    resolver(lz.b)                       # el boceto sigue siendo resoluble
    assert lz.resultado.ok

    if radio is None:                    # rechazado: queda abierto, sin geometría ni historial nuevos
        assert lz.entrada is entrada and lz.b.a_dict() == antes and not lz.historial
        assert mensajes
        aviso = mensajes[-1]
        assert "\n" not in aviso and "\r" not in aviso and len(aviso) <= 80, aviso
        _escribir(campo, "50")           # se recupera: la app sigue viva y el boceto no queda roto
        QApplication.instance().processEvents()
        assert lz.entrada is None and len(_circulos(lz)) == 1
    else:                                # aceptado: un círculo con el radio que manda el diámetro
        assert lz.entrada is None and not mensajes
        (circulo,) = _circulos(lz)
        assert lz.b.radio(circulo.id) == pytest.approx(radio, abs=1e-8)
        assert lz.historial

    if lz.entrada is not None:
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()
