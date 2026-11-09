"""B-269: la vista previa se muestra en el visor y solo al aceptar entra al navegador."""
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_cuerpo_de_previa_solo_aparece_en_navegador_al_aceptar(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    boceto = Boceto()
    boceto.agregar_rectangulo((0, 0), (20, 10))
    op_id = doc.nuevo_id()
    doc.agregar(OpBoceto(op_id, "Rectángulo", plano="XY", boceto=boceto))
    prefs = Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(doc=doc, prefs=prefs)
    try:
        v.show()
        app.processEvents()
        panel = v.ejecutar_comando(CATALOGO["extruir"]())
        assert panel is not None
        assert panel.elegir_boceto(op_id)
        panel.set_valor("distancia", "5 mm")
        panel._t_previa.stop()
        panel._calcular_previa()
        QTest.qWait(10)

        assert v._estado_previa is not None
        nuevos = set(v._estado_previa.cuerpos) - set(v.doc.estado_final.cuerpos)
        assert len(nuevos) == 1
        cuerpo_id = nuevos.pop()
        assert cuerpo_id in {m["id"] for m in v.visor._mallas}
        assert cuerpo_id not in v.navegador._items

        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        QTest.qWait(10)
        assert v.panel is None
        assert cuerpo_id in v.doc.estado_final.cuerpos
        assert cuerpo_id in v.navegador._items
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
