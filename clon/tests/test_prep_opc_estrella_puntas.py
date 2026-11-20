# -*- coding: utf-8 -*-
"""PREP: opción «Puntas (Entero)» del comando «Estrella» del boceto.

El spinbox entero (min 3, max 64) cambia la cantidad de puntas de la estrella recién dibujada
(P-154: se rehace). Se prueba un valor numérico y los dos bordes del rango.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.ui.preferencias import Preferencias  # noqa: E402
from omnicad.ui.ventana import VentanaPrincipal  # noqa: E402


@pytest.fixture
def boceto(tmp_path):
    QApplication.instance() or QApplication([])
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    v._iniciar_boceto(Boceto(), geo.Plano("XY"), {"op": None, "plano": "XY", "marco": None})
    QTest.qWait(50)
    yield v.modo_boceto
    v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()


def _clic(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _teclear(sp, texto):
    sp.setFocus()
    QTest.keyClick(sp, Qt.Key_A, Qt.ControlModifier)
    for ch in texto:
        QTest.keyClick(sp, ch)


def _spin(mb, etiqueta):
    form = mb.tarjeta.form_contexto
    for i in range(form.rowCount()):
        if form.itemAt(i, form.ItemRole.LabelRole).widget().text() == etiqueta:
            return form.itemAt(i, form.ItemRole.FieldRole).widget()
    raise AssertionError(f"la tarjeta no tiene «{etiqueta}»")


def _lineas(lz):
    return sum(1 for c in lz.b.curvas.values() if c.tipo == "linea" and not c.construccion)


@pytest.mark.parametrize("puntas", [5, 3, 64])
def test_puntas_entero_cambia_la_cantidad_de_lados(boceto, puntas):
    mb = boceto
    lz = mb.lienzo
    mb.acciones["sk_estrella"].trigger()
    _clic(lz, 0, 0)
    _clic(lz, 0, 15)
    _teclear(_spin(mb, "Puntas"), str(puntas))
    assert _lineas(lz) == 2 * puntas and lz.resultado.ok
