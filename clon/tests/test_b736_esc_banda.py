# -*- coding: utf-8 -*-
"""B-736: Esc a mitad del arrastre de una ventana cancela la banda; soltar el botón después no hace zoom ni selecciona."""
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture
def visor():
    from omnicad.ui import visor3d as vis
    QApplication.instance() or QApplication([])
    v = vis.Visor3D()
    v.resize(800, 600)
    yield v
    v.deleteLater()


@pytest.mark.parametrize("modo", ["ventana", "sel_ventana"])
def test_esc_cancela_la_banda(visor, modo):
    visor.set_modo(modo)
    visor._empezar_banda(QPoint(100, 100))
    visor.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    assert visor._banda_inicio is None and not visor._banda.isVisible() and visor.modo is None
    zooms, regiones = [], []
    visor.zoom_ventana = zooms.append
    visor.seleccion_region.connect(lambda *a: regiones.append(a))
    p = QPointF(300, 300)
    visor.mouseReleaseEvent(QMouseEvent(QEvent.MouseButtonRelease, p, p, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    assert zooms == [] and regiones == []
