"""TXT-9: un comando que pide perfil avisa cuando el clic cayó en un trazo con la región rellena debajo."""
import numpy as np
from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_txt9_clic_en_el_trazo_avisa_y_en_el_relleno_no(tmp_path):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_sketch", {"plane": "XY", "name": "B"})["ok"]
    assert api.llamar(sesion, "draw_rectangle", {"sketch": "B", "x1": 0, "y1": 0, "x2": 40, "y2": 20})["ok"]
    v = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    try:
        QTest.qWait(300)
        v.acciones["vista_arriba"].trigger()
        v.visor.encuadrar()
        QTest.qWait(200)
        panel = v.ejecutar_comando(CATALOGO["sup_extruir"]())     # acepta curvas y perfiles a la vez
        QTest.qWait(200)
        toast = v.area.toast

        # centro del relleno: elige el perfil y no avisa
        QTest.mouseClick(v.visor, Qt.LeftButton, pos=v.visor.proyectar(np.array([20.0, 10, 0])).toPoint())
        QTest.qWait(100)
        assert [h["ref"]["tipo"] for h in panel.valores["curvas"]] == ["perfil"]
        assert not toast.isVisible()

        # 4 px adentro del lado de abajo: gana el trazo (como Fusion) y avisa que el relleno estaba debajo
        borde, adentro = (v.visor.proyectar(np.array([20.0, y, 0])) for y in (0, 1))
        paso = adentro - borde
        q = borde + paso * (4 / np.hypot(paso.x(), paso.y()))
        QTest.mouseClick(v.visor, Qt.LeftButton, pos=QPointF(q).toPoint())
        QTest.qWait(100)
        assert "curva_boceto" in [h["ref"]["tipo"] for h in panel.valores["curvas"]]
        assert toast.isVisible() and "trazo" in toast.texto.text()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
