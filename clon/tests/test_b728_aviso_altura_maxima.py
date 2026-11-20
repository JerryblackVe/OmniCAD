"""B-728: teclear una altura de texto mayor que el máximo avisa en 1 renglón en vez de recortar en silencio."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.ui import modo_boceto


def test_altura_mayor_que_el_maximo_avisa():
    QApplication.instance() or QApplication([])
    panel = modo_boceto.PanelCaracter()
    avisos = []
    panel.altura.excedido.connect(avisos.append)
    panel.show()
    panel.altura.setFocus()
    panel.altura.selectAll()
    QTest.keyClicks(panel.altura, "99999999")
    QTest.keyClick(panel.altura, Qt.Key_Return)
    assert avisos and avisos[0] == panel.altura.maximum()
    assert panel.altura.value() == 9999.0
    panel.altura.selectAll()
    avisos.clear()
    QTest.keyClicks(panel.altura, "12")
    assert not avisos
    panel.deleteLater()
