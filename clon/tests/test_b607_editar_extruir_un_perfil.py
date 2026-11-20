"""B-607: Editar Extruir de un perfil de Boceto2 (coplanar con Boceto1) abría con 2 perfiles y no dejaba aceptar."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _sesion():
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="Boceto1")
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=143, y2=106)
    _llamar(s, "extrude", sketch="Boceto1", profile=[0], distance="10 mm")
    _llamar(s, "fillet", edges="|Z", body="Cuerpo1", radius=5)
    _llamar(s, "create_sketch", plane="XY", name="Boceto2")
    _llamar(s, "draw_rectangle", x1=-17, y1=-17, x2=160, y2=123)
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=143, y2=106)
    perfiles = _llamar(s, "get_sketch")["profiles"]
    marco = next(i for i, p in enumerate(perfiles) if abs(p["area"] - (177 * 140 - 143 * 106)) < 1)
    _llamar(s, "extrude", sketch="Boceto2", profile=[marco], extent="all", operation="new_body")
    return s


def _volumenes(s):
    return {k: round(geo.volumen(c.forma), 1) for k, c in s.doc.estado_final.cuerpos.items()}


def test_editar_extruir_muestra_solo_el_perfil_elegido(tmp_path, app):
    s = _sesion()
    antes = _volumenes(s)
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    app.processEvents()
    try:
        v.navegador.arbol.setCurrentItem(v.navegador.item("op1"))     # lo último que tocó la persona: Boceto1
        app.processEvents()
        v.editar_operacion(s.doc.operaciones[-1].id)
        QTest.qWait(300)
        panel = v.panel
        assert panel is not None
        assert len(panel.valores["perfiles"]) == 1, [h["ref"] for h in panel.valores["perfiles"]]
        for _ in range(300):
            if panel.boton_ok.isEnabled():
                break
            QTest.qWait(20)
        assert panel.boton_ok.isEnabled()
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        for _ in range(300):
            if v.panel is None:
                break
            QTest.qWait(20)
        assert v.panel is None
        assert _volumenes(s) == antes
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
