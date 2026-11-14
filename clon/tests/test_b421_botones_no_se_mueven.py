"""B-421: Aceptar y Cancelar no se mueven mientras el panel está abierto, aunque aparezcan o se vayan campos (los de
«Objetos» al pasar la Operación a Cortar o Intersecar): un clic en el lugar de antes no puede caer en el vacío."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _centros(panel):
    return [b.mapTo(panel.window(), b.rect().center()) for b in (panel.boton_ok, panel.boton_cancelar)]


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 10})["ok"]
    assert api.llamar(s, "sketch_from_spec", {"plane": "XY", "entities": [
        {"type": "rectangle", "corner1": [0, 0], "corner2": [30, 20]}]})["ok"]
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    app.processEvents()
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("comando", ["extruir", "revolucion"])
def test_los_botones_no_se_mueven_al_aparecer_el_campo_objetos(ventana, comando):
    panel = ventana.ejecutar_comando(CATALOGO[comando]())
    QTest.qWait(400)                                      # el panel asienta su alto
    antes = _centros(panel)
    altos = [panel.height()]
    for operacion in ("unir", "cortar", "intersecar", "nuevo"):
        panel.set_valor("operacion", operacion)
        QTest.qWait(120)
        altos.append(panel.height())
        assert _centros(panel) == antes, f"Aceptar/Cancelar se movieron con la operación «{operacion}»"
    assert len(set(altos)) > 1, "el panel no cambió de alto: la prueba no prueba nada"


def test_los_botones_no_se_mueven_al_cambiar_el_tipo_de_radio_del_empalme(ventana):
    """Empalme › Tipo de radio: «Variable» suma «Radio final» y «Puntos intermedios» (Aceptar bajaba 15 px)."""
    panel = ventana.ejecutar_comando(CATALOGO["empalme_3d"]())
    QTest.qWait(400)
    antes, altos = _centros(panel), [panel.height()]
    for tipo in ("variable", "asimetrico", "cuerda", "constante", "variable"):
        panel.set_valor("tipo_radio", tipo)
        QTest.qWait(120)
        altos.append(panel.height())
        assert _centros(panel) == antes, f"Tipo de radio {tipo}: los botones se movieron ({altos})"
    assert len(set(altos)) > 1
