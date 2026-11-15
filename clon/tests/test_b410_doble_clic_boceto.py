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
        assert "Doble clic para editarlo" in mensaje and "F2 para renombrarlo" in mensaje
        assert not v.modo_boceto.activo

        QTest.mouseDClick(arbol.viewport(), Qt.LeftButton, pos=punto)
        app.processEvents()
        # B-540: en Fusion el doble clic edita el boceto; renombrar es el doble clic LENTO, F2 o el clic derecho
        assert v.modo_boceto.activo, "La barra promete editar y no abrió el boceto"
        assert not any(e.isVisible() for e in arbol.findChildren(QLineEdit))
    finally:
        if v.modo_boceto.activo:
            v.modo_boceto.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
