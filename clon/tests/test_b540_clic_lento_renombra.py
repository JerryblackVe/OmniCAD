"""B-540: en el navegador, el clic lento (dos clics pausados sobre el nombre) renombra en el lugar, como Fusion
(docs/fusion_docs › Rename objects: «Slow double-click the object's name»); el doble clic edita el boceto."""
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_clic_lento_renombra_y_doble_clic_no(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    boceto = Boceto()
    boceto.agregar_rectangulo((0, 0), (20, 10))
    op = OpBoceto(doc.nuevo_id(), "Boceto1", plano="XY", boceto=boceto)
    doc.agregar(op)
    v = VentanaPrincipal(doc=doc, prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    pausa = QApplication.doubleClickInterval() + 150
    try:
        v.resize(1280, 800)
        v.show()
        app.processEvents()
        arbol = v.navegador.arbol

        def clic(doble=False):
            fila = v.navegador.item(op.id)
            arbol.scrollToItem(fila)
            rect = arbol.visualItemRect(fila)
            punto = QPoint(rect.left() + 75, rect.center().y())     # sobre el nombre
            (QTest.mouseDClick if doble else QTest.mouseClick)(arbol.viewport(), Qt.LeftButton, pos=punto)
            app.processEvents()

        def caja_abierta():
            return any(e.isVisible() for e in arbol.findChildren(QLineEdit))

        clic()
        QTest.qWait(pausa)
        assert not caja_abierta()                       # un solo clic elige, no renombra
        clic()
        QTest.qWait(pausa)
        assert caja_abierta() and not v.modo_boceto.activo
        QTest.keyClick(QApplication.focusWidget(), Qt.Key_Escape)
        app.processEvents()

        QTest.qWait(pausa)
        clic(doble=True)                                # el doble clic edita y cancela el clic lento
        QTest.qWait(pausa)
        assert v.modo_boceto.activo and not caja_abierta()
    finally:
        if v.modo_boceto.activo:
            v.modo_boceto.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
