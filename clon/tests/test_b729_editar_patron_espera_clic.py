"""B-729: «Editar patrón» sin selección arma una espera de clic; el clic en una copia (o en el original) abre el panel."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import editor_boceto


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _clic(lz, x, y):
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _patron(lz):
    cid = lz.b.agregar_circulo((30, 10), 4)
    lz.b.patron_circular([cid], (0, 0), 5)
    lz.resolver()
    lz.encuadrar()
    return cid


def test_sin_seleccion_arma_la_espera_y_el_clic_en_una_copia_abre_el_panel(lienzo):
    lz = lienzo
    _patron(lz)
    copia = next(iter(lz.b.patrones[0]["copias"]["0"]))
    cx, cy = lz.b.coords(lz.b.curvas[copia].centro)
    lz.seleccion = []
    assert lz.editar_patron() is False and lz.herramienta == "editar_patron"
    _clic(lz, cx + lz.b.curvas[copia].radio, cy)
    assert lz.patron.activo and lz.herramienta == "patron_circular"


def test_clic_en_una_curva_ajena_avisa_y_sigue_esperando(lienzo):
    lz = lienzo
    _patron(lz)
    lz.b.agregar_linea((-40, -30), (-10, -30))
    lz.resolver()
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.set_herramienta("editar_patron")
    _clic(lz, -25, -30)
    assert avisos[-1] == "Esa curva no es de un patrón." and lz.herramienta == "editar_patron"
    assert not lz.patron.activo
