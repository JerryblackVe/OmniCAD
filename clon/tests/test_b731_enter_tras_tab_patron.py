"""B-731: en el Patrón circular, Enter después de Tab desde Cantidad acepta (el foco no cae en el área de scroll)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.ui.panel_patron import PanelPatron


@pytest.mark.parametrize("tipo, ultimo", [("circular", "cantidad"), ("rectangular", "cantidad1")])
def test_enter_tras_tab_acepta(tipo, ultimo):
    app = QApplication.instance() or QApplication([])
    p = PanelPatron()
    p.configurar(tipo)
    p.show()
    p.activateWindow()
    p.campos[ultimo].setFocus()
    app.processEvents()
    aceptado = []
    p.aceptado.connect(lambda: aceptado.append(1))
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Tab)
    app.processEvents()
    assert QApplication.focusWidget() in p.campos.values()
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Return)
    assert aceptado == [1]
    p.deleteLater()
