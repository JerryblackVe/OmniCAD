# -*- coding: utf-8 -*-
"""E11 (tanda 13): el primer clic en Aceptar de Extruir «no hizo nada». Al teclear la distancia se iba el mensaje rojo de
varias líneas, el panel se achicaba y Aceptar subía: el clic caía donde estaba antes. Mientras el panel está abierto, la
zona del mensaje no se achica."""
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_aceptar_no_se_mueve_cuando_se_va_el_mensaje(tmp_path):
    s = api.Sesion()
    assert api.llamar(s, "sketch_from_spec", {"plane": "XY", "entities": [
        {"type": "rectangle", "corner1": [0, 0], "corner2": [30, 20]}]})["ok"]
    boceto = s.doc.operaciones[-1].id
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(CATALOGO["extruir"]())
        p.set_valor("distancia", "0 mm")
        est = v.doc.estado_final
        ref = OpExtrusion.referencia_perfil(est.bocetos[boceto].perfiles[0])
        p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": boceto, **ref}, est))
        QTest.qWait(100)
        assert "no puede ser cero" in p.mensaje.text()
        antes = p.boton_ok.mapToGlobal(p.boton_ok.rect().center())
        p.set_valor("distancia", "15 mm")
        QTest.qWait(100)
        assert not p.mensaje.text() or "no puede ser cero" not in p.mensaje.text()
        assert p.boton_ok.mapToGlobal(p.boton_ok.rect().center()) == antes
        assert p.height() < 2 * p.sizeHint().height()            # y el panel no quedó con un alto absurdo
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
