"""B-409: Esc descarta el panel desde cualquier zona de la ventana, sin tocar el documento."""

import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QVBoxLayout

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


COMANDOS = [
    ("extruir", Qt.Key_E, Qt.NoModifier, "distancia"),
    ("empalme_3d", Qt.Key_F, Qt.NoModifier, "radio"),
    ("chaflan_3d", Qt.Key_Backslash, Qt.ControlModifier, "distancia"),
    ("agujero", Qt.Key_H, Qt.NoModifier, "diametro"),
    ("mover_copiar", Qt.Key_M, Qt.NoModifier, "distancia"),
    ("pulsar_tirar", Qt.Key_Q, Qt.NoModifier, "distancia"),
]


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="30", alto="10"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    v.activateWindow()
    app.processEvents()
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def abrir(ventana, clave, tecla, modificador):
    QTest.mouseClick(ventana.visor, Qt.LeftButton, Qt.NoModifier, QPoint(20, 20))
    QTest.keyClick(ventana.visor, tecla, modificador)
    QApplication.processEvents()
    panel = ventana.panel
    assert panel is not None and panel.comando.CLAVE == clave
    assert ventana.visor.hasFocus()
    return panel


@pytest.mark.parametrize("clave,tecla,modificador,campo", COMANDOS, ids=[c[0] for c in COMANDOS])
@pytest.mark.parametrize("zona", ["inicial", "visor", "titulo", "boton", "campo", "navegador"])
def test_esc_descarta_desde_cualquier_zona(ventana, clave, tecla, modificador, campo, zona):
    receta = ventana.doc.a_dict()
    modificado = ventana.doc.modificado
    estado = ventana.doc.estado_final
    panel = abrir(ventana, clave, tecla, modificador)
    destino = {
        "inicial": ventana.visor,
        "visor": ventana.visor,
        "titulo": panel.titulo,
        "boton": next(iter(panel.filas_sel.values())).boton,
        "campo": next((w for w in (panel.widgets[campo], *panel.widgets.values()) if isinstance(w, QLineEdit) and w.isVisible()), None),
        "navegador": ventana.navegador,
    }[zona]
    if zona != "inicial":
        if zona in ("boton", "campo"):
            panel.desplazador.ensureWidgetVisible(destino)
        QTest.mouseClick(destino, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        QApplication.processEvents()
    # La cabecera no toma foco: el clic deja el teclado en el visor, como en el reporte.
    if zona in ("inicial", "visor", "titulo"):
        assert ventana.visor.hasFocus()
    elif zona in ("boton", "campo"):
        assert destino.hasFocus()
    QTest.keyClick(destino, Qt.Key_Escape)
    assert ventana.panel is None, f"Esc no canceló {clave} desde {zona}"
    assert not panel.isVisible() and panel.cerrando
    QApplication.processEvents()
    assert ventana.doc.a_dict() == receta
    assert ventana.doc.modificado == modificado
    assert ventana.doc.estado_final is estado


@pytest.mark.parametrize("clave,tecla,modificador,campo", COMANDOS, ids=[c[0] for c in COMANDOS])
def test_esc_en_un_modal_solo_cierra_el_modal(ventana, clave, tecla, modificador, campo):
    receta = ventana.doc.a_dict()
    panel = abrir(ventana, clave, tecla, modificador)
    dialogo = QDialog(ventana)
    dialogo.setModal(True)
    entrada = QLineEdit(dialogo)
    QVBoxLayout(dialogo).addWidget(entrada)
    dialogo.show()
    dialogo.activateWindow()
    QApplication.processEvents()
    try:
        QTest.mouseClick(entrada, Qt.LeftButton)
        assert QApplication.activeModalWidget() is dialogo
        QTest.keyClick(entrada, Qt.Key_Escape)
        assert not dialogo.isVisible() and dialogo.result() == QDialog.Rejected
        assert ventana.panel is panel and panel.isVisible()
        assert ventana.doc.a_dict() == receta
    finally:
        dialogo.close()
        dialogo.deleteLater()
