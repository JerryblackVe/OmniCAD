"""Valores raros del campo «ancho» del comando de boceto «sk_ranura_arco_centro» (ranura de arco de punto
central): vacío, 0, negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el
boceto roto, y todo aviso es de un renglón. Equivale al paso «Specify the width of the slot» de
SKT-CREATE-SLOTS (docs/fusion_docs/contenido/fusion-sketch/create-slots-in-a-sketch-*.md)."""
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

XFAIL_VACIO = pytest.mark.xfail(reason="B-818: el ancho vacío se acepta en silencio y crea la ranura con el ancho del "
                                        "ratón", strict=True)

# El ancho es una cota de distancia: > 0 y hasta 1 km (validar_valor_cota).
CASOS = [
    pytest.param("", False, None, id="ancho_vacio", marks=XFAIL_VACIO),
    pytest.param("0", False, None, id="ancho_cero"),
    pytest.param("-5", False, None, id="ancho_negativo"),
    pytest.param("2000000", False, None, id="ancho_enorme"),
    pytest.param("20 mm", True, 20.0, id="ancho_unidad"),
    pytest.param("5*2", True, 10.0, id="ancho_expresion"),
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
    """Centro (0,0), radio 20, barrido 90° y cursor a 30 mm: el ancho del ratón sería 20 mm."""
    lz.set_herramienta("ranura_arco_centro")
    _clic(lz, 0, 0)
    _clic(lz, 20, 0)
    _clic(lz, 0, 20)
    _mover(lz, 30, 0)
    lz._activo = 0
    lz._editar_campo_vivo("0")
    assert lz.entrada is not None, "la caja del ancho no se abrió"


def _escribir(widget, texto):
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    if texto:
        QTest.keyClicks(widget, texto)
    else:
        QTest.keyClick(widget, Qt.Key_Backspace)
    QTest.keyClick(widget, Qt.Key_Return)


def _tapas(lz):
    radios = [lz.b.radio(curva.id) for curva in lz.b.curvas.values() if curva.tipo == "arco"]
    return sorted(r for r in radios if r > 1e-9)


@pytest.mark.parametrize(("texto", "valido", "esperado"), CASOS)
def test_valores_raros_de_sk_ranura_arco_centro_no_rompen_el_boceto(lienzo, texto, valido, esperado):
    lz = lienzo
    _preparar(lz)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    antes = lz.b.a_dict()

    widget = lz.entrada.campos[0]
    entrada = lz.entrada
    _escribir(widget, texto)

    if not valido:
        assert lz.entrada is entrada
        assert lz.b.a_dict() == antes
        assert not lz.historial
        assert lz.resultado.ok
        assert mensajes
        assert all("\n" not in m and "\r" not in m for m in mensajes)
        _escribir(widget, "10")                      # limpieza: completa la ranura y no deja el campo abierto
    else:
        assert lz.entrada is None
        assert not mensajes

    tapas = _tapas(lz)
    assert len(tapas) >= 4
    assert tapas[0] == pytest.approx((10.0 if not valido else esperado) / 2)
    assert lz.resultado.ok
    assert resolver(lz.b).ok
    assert lz.historial
    assert lz.isVisible()
