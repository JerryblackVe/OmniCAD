"""B-638: Alargar en el editor de boceto no cambia la curva. El clic simulado sí la alarga hasta la recta
proyectada: el bug no se reprodujo con este caso, así que queda como regresión."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo.geometria import Plano
from omnicad.restricciones import Boceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui.editor_boceto import Lienzo


def test_alargar_con_clic_hasta_recta_proyectada():
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    linea = b.agregar_linea((5, 10), (20, 10))
    b.agregar_proyeccion([("linea", None, (30, 5), (30, 15))])
    lienzo = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    lienzo.show()
    try:
        app.processEvents()
        lienzo.set_herramienta("alargar")
        QTest.mouseClick(lienzo, Qt.LeftButton, pos=lienzo.a_px(19, 10).toPoint())
        inicio, fin = b._extremos_linea(linea)
        assert fin == pytest.approx((30, 10))
        assert inicio == pytest.approx((5, 10))
    finally:
        lienzo.close()
