"""B-431: Extruir, Revolución, Barrido y Solevación arrancan en «Cuerpo nuevo» aunque el último uso o el preajuste
guardaran «Cortar» (Fusion propone «New Body»); fijada a mano o al editar un paso, la operación se respeta."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import preajustes
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_PREAJUSTES", str(tmp_path / "preajustes.json"))
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    assert api.llamar(sesion, "sketch_from_spec", {"plane": "XY", "entities": [
        {"type": "circle", "center": [50, 0], "radius": 5}]})["ok"]
    v = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        yield sesion, v
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("origen", ["ultimo", "preajuste"])
@pytest.mark.parametrize("clave", ["extruir", "revolucion", "barrido", "solevacion"])
def test_la_operacion_inicial_es_cuerpo_nuevo(ventana, clave, origen):
    sesion, v = ventana
    if origen == "ultimo":
        preajustes.guardar_ultimo(clave, {"operacion": "cortar"})
        api.llamar(sesion, "manage_command_presets", {"command": clave, "action": "set_default", "default": "last_used"})
    else:
        api.llamar(sesion, "manage_command_presets", {"command": clave, "action": "save", "name": "Corte",
                                                      "values": {"operacion": "cortar"}})
        api.llamar(sesion, "manage_command_presets", {"command": clave, "action": "set_default", "default": "Corte"})
    panel = v.ejecutar_comando(CATALOGO[clave]())
    assert panel.widgets["operacion"].currentData() == "nuevo"
    assert panel.valores["operacion"] == "nuevo"
    panel.set_valor("operacion", "cortar")     # lo que la persona elige a mano se respeta
    assert panel.valores["operacion"] == "cortar"
