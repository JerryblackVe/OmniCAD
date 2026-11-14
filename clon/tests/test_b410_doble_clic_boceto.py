"""B-410: el doble clic del navegador cumple lo que anuncia la barra de estado."""
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_doble_clic_en_boceto_hace_lo_que_dice_la_barra(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    boceto = Boceto()
    for x in (0, 30, 60):
        boceto.agregar_rectangulo((x, 0), (x + 20, 10))
    op = OpBoceto(doc.nuevo_id(), "Boceto1", plano="XY", boceto=boceto)
    doc.agregar(op)
    prefs = Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(doc=doc, prefs=prefs)
    try:
        v.resize(1280, 800)
        v.show()
        app.processEvents()
        arbol = v.navegador.arbol
        fila = v.navegador.item(op.id)
        arbol.scrollToItem(fila)
        rect = arbol.visualItemRect(fila)
        punto = QPoint(rect.left() + 75, rect.center().y())  # nombre, después del ojo y del ícono
        assert arbol.itemAt(punto) is fila

        QTest.mouseClick(arbol.viewport(), Qt.LeftButton, pos=punto)
        app.processEvents()
        mensaje = v.timeline.estado.toolTip()  # texto completo, sin el recorte visual de la barra
        assert mensaje.startswith("Boceto1: 3 perfil(es) cerrado(s).")
        assert "Doble clic para renombrarlo" in mensaje and "Editar boceto" in mensaje
        assert not v.modo_boceto.activo

        QTest.mouseDClick(arbol.viewport(), Qt.LeftButton, pos=punto)
        app.processEvents()
        # Fusion (docs/fusion_docs, «Rename objects»): el doble clic sobre el nombre lo renombra; editar va por el clic derecho
        assert not v.modo_boceto.activo
        assert any(e.isVisible() for e in arbol.findChildren(QLineEdit)), "La barra promete renombrar y no abrió el campo"
    finally:
        if v.modo_boceto.activo:
            v.modo_boceto.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
