"""B-737: en el Patrón, Tab desde el último campo vuelve al primero (no salta a otro botón de la ventana) y Mayús+Tab al revés."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from omnicad.ui.panel_patron import PanelPatron


@pytest.mark.parametrize("tipo", ["circular", "rectangular"])
def test_tab_da_la_vuelta_dentro_del_panel(tipo):
    app = QApplication.instance() or QApplication([])
    ventana = QWidget()
    lay = QVBoxLayout(ventana)
    p = PanelPatron()
    p.configurar(tipo)
    lay.addWidget(p)
    afuera = QPushButton("Panel de datos")          # el botón de la ventana al que saltaba el foco
    lay.addWidget(afuera)
    ventana.show()
    ventana.activateWindow()
    app.processEvents()
    visibles = [w for w in p.findChildren(QWidget) if w.focusPolicy() != Qt.NoFocus and w.isVisibleTo(p) and w.isEnabled()]
    primero, ultimo = visibles[0], visibles[-1]
    ultimo.setFocus()
    app.processEvents()
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Tab)
    app.processEvents()
    assert QApplication.focusWidget() is primero
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Backtab)
    app.processEvents()
    assert QApplication.focusWidget() is ultimo
    ventana.deleteLater()
