# -*- coding: utf-8 -*-
"""B-648/B-553: el tercer clic selecciona toda la expresión, incluida su unidad."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.timeline.parametros import LONGITUD  # noqa: E402
from omnicad.ui.campo_expresion import CampoExpresion  # noqa: E402


@pytest.mark.parametrize("valor", ["0,5 mm", "17,19 mm"])
def test_triple_clic_selecciona_numero_y_unidad(valor):
    app = QApplication.instance() or QApplication([])
    campo = CampoExpresion(valor, SimpleNamespace(parametros=[]), LONGITUD)
    campo.resize(240, 30)
    campo.show()
    campo.setFocus()
    QTest.qWait(10)
    try:
        primero = QPoint(8, campo.height() // 2)
        tercero = primero + QPoint(app.startDragDistance() + 2, 0)
        QTest.mouseDClick(campo, Qt.LeftButton, Qt.NoModifier, primero)
        assert campo.selectedText() != valor
        QTest.mouseClick(campo, Qt.LeftButton, Qt.NoModifier, tercero)
        assert campo.selectedText() == valor
        QTest.keyClicks(campo, "2 mm")
        assert campo.text() == "2 mm"
    finally:
        campo.close()
        campo.deleteLater()
