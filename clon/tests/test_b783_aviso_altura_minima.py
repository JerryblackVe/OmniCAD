"""B-783: teclear una altura de texto 0 o negativa avisa en 1 renglón en vez de volver a 5,00 sin mensaje."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.ui import modo_boceto


@pytest.mark.parametrize("tecleado, queda", [("0", 5.0), ("-3", 3.0)])    # el «-» se rechaza con aviso
def test_altura_menor_que_el_minimo_avisa(tecleado, queda):
    QApplication.instance() or QApplication([])
    panel = modo_boceto.PanelCaracter()
    avisos = []
    panel.altura.insuficiente.connect(avisos.append)
    panel.show()
    panel.altura.setValue(5.0)
    panel.altura.setFocus()
    panel.altura.selectAll()
    QTest.keyClicks(panel.altura, tecleado)
    QTest.keyClick(panel.altura, Qt.Key_Return)
    assert avisos and avisos[0] == panel.altura.minimum()
    assert panel.altura.value() == queda
    panel.altura.selectAll()
    avisos.clear()
    QTest.keyClicks(panel.altura, "12")
    QTest.keyClick(panel.altura, Qt.Key_Return)
    assert not avisos and panel.altura.value() == 12.0
    panel.deleteLater()
