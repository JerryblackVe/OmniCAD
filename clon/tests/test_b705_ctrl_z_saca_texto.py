# -*- coding: utf-8 -*-
"""B-705: Ctrl+Z saca el texto recién aceptado en un paso (boceto)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui.editor_boceto import Lienzo
from omnicad.nucleo.geometria import Plano


@pytest.fixture
def lz():
    QApplication.instance() or QApplication([])
    b = Boceto()
    l = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    l.ajustar_grilla = False
    l.resize(800, 600)
    return b, l


def test_ctrl_z_saca_texto_recien_creado(lz):
    b, l = lz
    # crear un texto en un paso de deshacer
    l.aplicar_cambio(lambda: b.agregar_texto((0.0, 0.0), "ABC", 5.0, 0.0))
    textos = [c for c in b.curvas.values() if type(c).__name__ == "Texto"]
    assert len(textos) == 1 and textos[0].texto == "ABC"

    # Ctrl+Z por teclado debe sacarlo en un paso
    l.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier, "z"))
    textos = [c for c in b.curvas.values() if type(c).__name__ == "Texto"]
    assert len(textos) == 0, f"quedó el texto: {[t.texto for t in textos]}"
