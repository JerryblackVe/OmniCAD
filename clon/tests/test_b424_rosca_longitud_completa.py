"""B-424: con Longitud completa no se confunde el radio del tamaño con la longitud de la cara. B-497, como Fusion: en
modo parcial no hay asa de Tamaño, solo Desfase y Longitud."""
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.mark.parametrize("tamano", ["M0.35", "M20"])
def test_longitud_completa_muestra_el_tamano_sin_caja_y_parcial_solo_desfase_y_longitud(tmp_path, tamano):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_cylinder", {"radius": 10, "height": 60, "name": "Perno"})["ok"]
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    ventana.resize(1300, 850)
    ventana.show()
    try:
        QTest.qWait(200)
        ventana.acciones["vista_frente"].trigger()
        ventana.visor.encuadrar()
        QTest.qWait(100)
        panel = ventana.ejecutar_comando(CATALOGO["rosca"]())
        forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
        cara = next(c for c in refs.subformas(forma, "cara") if refs.firma_cara(c).get("geom") == "cilindro")
        punto = ventana.visor.proyectar(np.array(refs.firma_cara(cara)["centro"])).toPoint()
        QTest.mouseClick(ventana.visor, Qt.LeftButton, pos=punto)
        assert panel.valores["caras"]

        casilla = panel.widgets["largo_completo"]
        assert casilla.isChecked()
        QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
        assert not panel.valores["largo_completo"]
        combo = panel.widgets["tam_iso_metrica"]
        combo.setFocus()
        QTest.keyClick(combo, Qt.Key_Home)
        for _ in range(combo.findData(tamano)):
            QTest.keyClick(combo, Qt.Key_Down)
        assert panel.valores["tam_iso_metrica"] == tamano
        gestor = panel.manipuladores
        assert [m.clave for m in gestor.manips] == ["desfase", "longitud"]
        assert set(gestor.cajas) == {"desfase", "longitud"} and gestor.cajas["longitud"].text() == "10 mm"

        QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
        assert panel.valores["largo_completo"]
        assert not gestor.cajas, {clave: caja.text() for clave, caja in gestor.cajas.items()}
        assert [m.clave for m in gestor.manips] == ["tam_iso_metrica"]
        assert panel.valores["tam_iso_metrica"] == tamano

        QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
        assert not panel.valores["largo_completo"]
        assert [m.clave for m in gestor.manips] == ["desfase", "longitud"]
        assert set(gestor.cajas) == {"desfase", "longitud"} and gestor.cajas["longitud"].text() == "10 mm"
        assert panel.valores["tam_iso_metrica"] == tamano
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        sesion.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()
