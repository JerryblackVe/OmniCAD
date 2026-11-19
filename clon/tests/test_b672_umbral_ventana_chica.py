"""B-672: el umbral de «ventana chica» debe plegar el navegador y Opciones antes de que tapen el visor."""
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
    v.modo_boceto.iniciar(Boceto(), g.Plano("XY"), {"op": None, "plano": "XY"})
    QTest.qWait(1)
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def test_b672_umbral_pliega_antes_de_que_tapen_el_visor(ventana):
    """Con el visor a ~416 px de alto el navegador y Opciones ya tapan demasiado: deben plegarse.

    En Windows esto pasa con la ventana a ~836×538 lógicos (el visor queda poco por encima del umbral viejo
    de 400 px); en Linux el visor es más alto, así que 900×600 reproduce la misma medida de visor (~416 px).
    """
    v = ventana
    v.resize(900, 600)                       # visor ~416 px de alto: por encima de 400, por debajo de 440
    QTest.qWait(1)
    assert v.navegador.arbol.isHidden(), "el navegador debe plegarse aunque el visor mida ~416 px de alto"
    assert v.modo_boceto.paleta.opciones.isHidden(), "Opciones debe plegarse aunque el visor mida ~416 px de alto"
