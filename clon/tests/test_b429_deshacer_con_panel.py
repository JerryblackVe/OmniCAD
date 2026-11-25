"""B-429: con un comando abierto, el primer Ctrl+Z lo cancela y no toca el timeline; el `undo` del MCP da APP_BUSY."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="30", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    v.activateWindow()
    app.processEvents()
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("clave", ["extruir", "caja"])
def test_ctrl_z_con_un_panel_abierto_lo_cancela_sin_deshacer_el_paso(ventana, clave):
    receta = ventana.doc.a_dict()
    panel = ventana.ejecutar_comando(CATALOGO[clave]())
    assert ventana.panel is panel
    ventana.visor.setFocus()
    QTest.keyClick(ventana.visor, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()
    assert ventana.panel is None and panel.cerrando
    assert ventana.doc.a_dict() == receta                      # el timeline no se tocó
    QTest.keyClick(ventana.visor, Qt.Key_Z, Qt.ControlModifier)  # el segundo Ctrl+Z sí deshace
    QApplication.processEvents()
    assert len(ventana.doc.operaciones) == 1


def test_undo_del_puente_con_un_comando_abierto_da_app_busy(ventana):
    from omnicad.ui.puente import PuenteAgentes
    ventana.ejecutar_comando(CATALOGO["extruir"]())
    r = PuenteAgentes(ventana).ejecutar("undo", {})
    assert r["error_kind"] == "APP_BUSY" and "comando" in r["mensaje"]
    assert len(ventana.doc.operaciones) == 2
