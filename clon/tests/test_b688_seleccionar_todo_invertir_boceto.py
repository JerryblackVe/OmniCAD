# -*- coding: utf-8 -*-
"""B-688: «Seleccionar todo» e «Invertir selección» de la cinta actúan sobre la geometría del boceto abierto."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto


@pytest.fixture
def ventana(tmp_path):
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
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _esperado(lienzo):
    """B-793: curvas y también sus puntos (como la ventana de selección y Fusion)."""
    return set(lienzo.b.curvas) | {p.id for p in lienzo.b.puntos.values() if p.id > 0}


def test_b688_seleccionar_todo_en_boceto(ventana):
    app = QApplication.instance()
    lienzo = ventana.modo_boceto.lienzo
    assert len(lienzo.b.curvas) == 5
    assert not lienzo.seleccion
    ventana.acciones["seleccionar_todo"].trigger()
    app.processEvents()
    assert set(lienzo.seleccion) == _esperado(lienzo)


def test_b688_invertir_seleccion_en_boceto(ventana):
    app = QApplication.instance()
    lienzo = ventana.modo_boceto.lienzo
    primera = next(iter(lienzo.b.curvas))
    lienzo.seleccion = [primera]
    app.processEvents()
    ventana.acciones["invertir_seleccion"].trigger()
    app.processEvents()
    assert set(lienzo.seleccion) == _esperado(lienzo) - {primera}
