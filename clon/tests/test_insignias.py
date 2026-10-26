# -*- coding: utf-8 -*-
"""Insignias de los íconos del timeline (ui/insignias.py): operación del paso y estado, siempre en la misma esquina."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.ui import insignias  # noqa: E402
from omnicad.ui.iconos import icono  # noqa: E402
from omnicad.ui.panel_timeline import PanelTimeline  # noqa: E402


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


class _Op:
    def __init__(self, **p):
        self.p = p


def test_insignia_de_manda_el_estado_sobre_la_operacion():
    assert insignias.insignia_de(_Op(operacion="cortar"), "ok") == "cortar"
    assert insignias.insignia_de(_Op(operacion="cortar"), "suprimida") == "cortar"
    assert insignias.insignia_de(_Op(operacion="cortar"), "error") == "error"
    assert insignias.insignia_de(_Op(operacion="nuevo"), "aviso") == "aviso"
    assert insignias.insignia_de(_Op(), "ok") is None
    assert insignias.insignia_de(_Op(operacion="caras"), "ok") is None       # «caras» de Desfase no es una operación de cuerpo


@pytest.mark.parametrize("nombre", sorted(insignias.DIBUJOS_INSIGNIA))
def test_la_insignia_pinta_solo_en_la_esquina_inferior_derecha(app_qt, nombre):
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    from PySide6.QtGui import QPainter
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(2, 2)
    insignias.DIBUJOS_INSIGNIA[nombre](p)
    p.end()
    img = pm.toImage()
    opacos = [(x, y) for x in range(64) for y in range(64) if img.pixelColor(x, y).alpha() > 40]
    assert len(opacos) > 80, f"{nombre}: casi no pinta"
    assert all(x >= 28 and y >= 28 for x, y in opacos), f"{nombre}: se sale de la esquina inferior derecha"


def test_el_timeline_pone_insignia_de_operacion_y_de_estado(app_qt):
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})            # operacion «nuevo»
    t = PanelTimeline()
    t.actualizar(s.doc)
    item = t.lista.item(0)
    con = item.icon().pixmap(24, 24).toImage()
    sin = icono("caja").pixmap(24, 24).toImage()
    assert con != sin, "el paso de cuerpo nuevo no lleva su insignia"
    assert "Operación: Cuerpo nuevo" in item.toolTip()
