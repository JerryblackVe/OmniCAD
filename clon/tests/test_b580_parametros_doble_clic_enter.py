"""B-580: en Parámetros (Ctrl+P), el doble clic en «Expresión» siempre entra a editar, aunque la tabla se rehaga entre
los dos clics (el recálculo del cambio anterior), y Enter confirma el valor sin cerrar el diálogo, como Fusion."""
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from omnicad.ui.dialogo_parametros import EXPRESION
from test_dialogo_parametros import app_qt, dlg, fila, s  # noqa: F401 — fixtures


def _doble_clic(d, nombre, rehacer_en_medio=False):
    """Clic, (la tabla se rehace), y el segundo clic, que Qt entrega como doble clic."""
    vista = d.arbol.viewport()
    pos = d.arbol.visualItemRect(fila(d, nombre)).topLeft()
    pos.setX(d.arbol.header().sectionViewportPosition(EXPRESION) + 10)
    pos.setY(pos.y() + 5)
    QTest.mouseClick(vista, Qt.LeftButton, pos=pos)
    if rehacer_en_medio:
        d._poblar()
    p = QPointF(pos)
    QApplication.sendEvent(vista, QMouseEvent(QEvent.MouseButtonDblClick, p, d.arbol.mapToGlobal(pos).toPointF(),
                                              Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    QTest.mouseRelease(vista, Qt.LeftButton, pos=pos)
    QTest.qWait(20)
    return d.arbol.findChild(QLineEdit)


def test_b580_doble_clic_edita_aunque_la_tabla_se_rehaga(dlg):  # noqa: F811
    assert _doble_clic(dlg, "w", rehacer_en_medio=True) is not None, "el doble clic no entró a editar"


def test_b580_enter_confirma_el_valor_y_no_cierra(dlg, s):  # noqa: F811
    editor = _doble_clic(dlg, "w")
    assert editor is not None
    editor.selectAll()
    QTest.keyClicks(editor, "12 mm")
    QTest.keyClick(editor, Qt.Key_Return)
    QTest.qWait(400)                                    # el editor se cierra y el cálculo automático aplica
    assert dlg.isVisible(), "Enter cerró el diálogo"
    assert s.doc.parametros.obtener("w").expresion == "12 mm"
