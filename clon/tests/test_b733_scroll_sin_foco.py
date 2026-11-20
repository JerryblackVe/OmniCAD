"""B-733: las áreas de scroll de los paneles no toman el foco con Tab (Enter seguiría aceptando; gemelo de B-731)."""
from PySide6.QtWidgets import QApplication, QScrollArea
from PySide6.QtCore import Qt

from omnicad.restricciones import Boceto
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import render as ur
from omnicad.ui.editor_boceto import Lienzo
from omnicad.ui.objetos_vectoriales import PanelObjetos


def test_areas_de_scroll_sin_foco():
    QApplication.instance() or QApplication([])
    lz = Lienzo(Boceto(), TablaParametros().evaluar)
    paneles = [PanelObjetos(lz.objetos, lz), ur.PanelEscena(), ur.PanelAspecto(crear_documento_ejemplo())]
    for p in paneles:
        areas = p.findChildren(QScrollArea)
        assert areas, type(p).__name__
        assert all(a.focusPolicy() == Qt.NoFocus for a in areas), type(p).__name__
    lz.deleteLater()
