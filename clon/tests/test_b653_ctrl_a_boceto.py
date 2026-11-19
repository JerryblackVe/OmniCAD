# -*- coding: utf-8 -*-
"""B-653: Ctrl+A en un boceto elige toda la geometría, como en Fusion."""
import pytest
from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto


@pytest.fixture
def lienzo(tmp_path):
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    b.agregar_rectangulo((-40, 0), (-20, 10))
    b.agregar_circulo((30, 10), 8)
    doc = Documento()
    doc.agregar(OpBoceto("sk", "Boceto1", boceto=b, plano="XY"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    app.processEvents()
    v.editar_operacion("sk")
    app.processEvents()
    yield v.modo_boceto.lienzo
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def test_b653_ctrl_a_selecciona_toda_la_geometria_del_boceto(lienzo):
    assert len(lienzo.b.curvas) == 5
    assert not lienzo.seleccion

    override = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key_A, Qt.ControlModifier, "a")
    QApplication.sendEvent(lienzo, override)
    assert override.isAccepted()                      # si no, el atajo de la ventana se come la tecla

    QTest.keyClick(lienzo, Qt.Key_A, Qt.ControlModifier)
    QApplication.processEvents()
    en_curvas = {p for c in lienzo.b.curvas.values() for p in c.puntos()}
    esperado = set(lienzo.b.curvas) | {p.id for p in lienzo.b.puntos.values()
                                       if p.id > 0 and p.id not in en_curvas}
    assert set(lienzo.seleccion) == esperado
