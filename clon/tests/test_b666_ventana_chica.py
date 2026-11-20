"""B-666: en una ventana chica el navegador y las opciones de la paleta de boceto se pliegan solos y no tapan el visor."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402


@pytest.fixture
def ventana(tmp_path):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    QTest.qWait(1)
    v.set_documento(Documento())
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _plegados(v):
    return v.navegador.arbol.isHidden(), v.modo_boceto.paleta.opciones.isHidden()


def test_b666_ventana_chica_pliega_navegador_y_opciones_y_al_agrandar_vuelven(ventana):
    v = ventana
    v.modo_boceto.iniciar(Boceto(), g.Plano("XY"), {"op": None, "plano": "XY"})
    QTest.qWait(1)
    assert _plegados(v) == (False, False)               # ventana grande: B-778, el Navegador sigue desplegado dentro del boceto
    v.resize(790, 510)                                  # el tamaño con que lo encontró E11
    QTest.qWait(1)
    paleta = v.modo_boceto.paleta
    assert _plegados(v) == (True, True)
    assert paleta.b_terminar.isVisible() and paleta.estado.isVisible()     # Terminar y el estado siguen a la vista
    visor = v.area.visor.geometry()
    tapado = sum(w.width() * w.height() for w in (v.navegador, paleta))
    assert tapado < 0.3 * visor.width() * visor.height()                     # antes tapaban más de la mitad
    paleta.b_opciones.click()                           # la persona las vuelve a abrir con un clic
    assert not paleta.opciones.isHidden() and paleta.b_opciones.text() == "▾ Opciones"
    v.resize(1200, 800)
    QTest.qWait(1)
    assert _plegados(v) == (False, False)               # lo que plegó la ventana chica se despliega solo


def test_b666_ventana_ya_chica_al_entrar_al_boceto(ventana):
    v = ventana
    v.resize(790, 510)
    QTest.qWait(1)
    v.modo_boceto.iniciar(Boceto(), g.Plano("XY"), {"op": None, "plano": "XY"})
    QTest.qWait(1)
    assert _plegados(v) == (True, True)
