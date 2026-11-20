# -*- coding: utf-8 -*-
"""Valores raros en los dos campos de la barra de «Línea de punto medio» (`sk_linea_medio`).

La ayuda oficial de Fusion («Create midpoint lines in a sketch», docs/fusion_docs/contenido/
fusion-sketch/create-midpoint-lines-in-a-sketch-*.md) dice que la herramienta pide la longitud y el ángulo
del segmento. En OmniCAD son los campos vivos `largo` y `angulo` de `editor_boceto_cotas.py`
(`_claves_vivas` / `_editar_campo_vivo`). Acá se escriben vacío, cero, negativo, enorme, con unidades y con
expresión en cada campo: nada cierra la app, deja el boceto roto ni emite un mensaje de más de un renglón.
"""
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

# (campo, valor tecleado, ¿queda abierta la barra porque se rechazó?)
# «5 mm» es largo válido pero ángulo ajeno; «90 deg» es ángulo válido pero largo ajeno.
CASOS = [
    ("largo", "", False),
    ("largo", "0", True),
    ("largo", "-5", True),
    ("largo", "1e9", True),
    ("largo", "5 mm", False),
    ("largo", "90 deg", True),
    ("largo", "5*2", False),
    ("largo", "ang", True),
    ("angulo", "", False),
    ("angulo", "0", False),
    ("angulo", "-5", False),
    ("angulo", "1e9", True),            # B-719: pasa de ANGULO_MAXIMO
    ("angulo", "5 mm", True),
    ("angulo", "90 deg", False),
    ("angulo", "5*2", False),
    ("angulo", "ang", True),
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


def _mover(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _clic(lz, x, y):
    _mover(lz, x, y)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _abrir(lz, campo):
    """Pone el punto medio, deja los dos campos vivos y abre la caja del campo pedido."""
    lz.set_herramienta("linea_medio")
    _clic(lz, 10, 20)
    _mover(lz, 40, 20)
    assert lz._claves_vivas() == ["largo", "angulo"]
    if campo == "angulo":
        # Como el usuario: tabular desde «largo» deja fijo ese valor y activa «angulo».
        lz._editar_campo_vivo("")
        lz.entrada.campos[0].setText("30")
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Tab)
        QApplication.instance().processEvents()
        assert "largo" in lz._bloqueos
    lz._editar_campo_vivo("")
    assert lz.entrada is not None


@pytest.mark.parametrize("campo,valor,queda_abierta", CASOS)
def test_raro_sk_linea_medio(lz, campo, valor, queda_abierta):
    antes = lz.b.a_dict()
    _abrir(lz, campo)
    lz.mensajes.clear()
    caja = lz.entrada.campos[0]
    caja.setText(valor)
    QTest.keyClick(caja, Qt.Key_Return)
    QApplication.instance().processEvents()

    assert (lz.entrada is not None) == queda_abierta, (campo, valor, lz.entrada is not None)
    assert all("\n" not in m for m in lz.mensajes), (campo, valor, lz.mensajes)
    if queda_abierta:
        assert lz.b.a_dict() == antes, (campo, valor, "el valor rechazado cambió el boceto")
        assert lz.mensajes, (campo, valor, "rechazo sin mensaje")
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()
    else:
        assert len(lz.b.curvas) == 1, (campo, valor, len(lz.b.curvas))

    try:
        resultado = resolver(lz.b)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed after {campo}={valor!r}: {e}")
    assert resultado.ok, (campo, valor, "el boceto quedó roto")
