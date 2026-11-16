"""B-548: en el Patrón, después de teclear la Cantidad, un clic en el rótulo «Extensión total» enfoca ese campo; lo que se
teclea va a la extensión, no se pierde ni cambia la cantidad."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def panel(tmp_path):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    respuesta = api.llamar(sesion, "create_box", {"length": 4, "width": 4, "height": 4})
    cuerpo = respuesta["result"]["bodies_created"][0]["id"]
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        ventana.resize(1280, 800)
        ventana.show()
        ventana.activateWindow()
        p = ventana.ejecutar_comando(CATALOGO["patron_rectangular_3d"]())
        p.set_valor("cuerpos", [hit_desde_ref({"tipo": "cuerpo", "cuerpo": cuerpo}, p.ctx.estado)])
        p.set_valor("dir1", [hit_desde_ref({"tipo": "eje", "id": "X"}, p.ctx.estado)])
        app.processEvents()
        yield p
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def test_clic_en_el_rotulo_de_la_extension_lleva_lo_tecleado_a_la_extension(panel):
    n1, d1 = panel.widgets["n1"], panel.widgets["d1"]
    QTest.mouseClick(n1.lineEdit(), Qt.LeftButton)
    QTest.keyClick(n1, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(n1, "4")
    QTest.mouseClick(panel.etiquetas["d1"], Qt.LeftButton)
    assert QApplication.focusWidget() is d1
    QTest.keyClicks(QApplication.focusWidget(), "380")      # el valor quedó seleccionado: se reemplaza entero
    assert panel.valores["n1"] == 4 and panel.valores["d1"] == "380"


def test_clic_en_el_rotulo_de_la_cantidad_la_enfoca(panel):
    QTest.mouseClick(panel.widgets["d1"], Qt.LeftButton)
    QTest.mouseClick(panel.etiquetas["n1"], Qt.LeftButton)
    QTest.keyClicks(QApplication.focusWidget(), "5")
    assert panel.valores["n1"] == 5
