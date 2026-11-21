"""B-779: la paleta de boceto no tapa el ViewCube: si no cabe con sus opciones, las pliega; con lugar, las despliega."""
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


def test_b779_paleta_no_tapa_el_cubo(ventana):
    v = ventana
    area, p = v.modo_boceto.paleta.parent(), v.modo_boceto.paleta
    for ancho, alto in ((1280, 720), (1100, 650)):
        v.resize(ancho, alto)
        QTest.qWait(5)
        assert not p.geometry().intersects(area.viewcube.geometry()), f"la paleta tapa el cubo a {ancho}x{alto}"
        assert p.b_terminar.isVisible()
    v.resize(1920, 1080)
    QTest.qWait(5)
    assert not p.opciones.isHidden(), "con lugar de sobra las opciones vuelven solas"
    assert not p.geometry().intersects(area.viewcube.geometry())
