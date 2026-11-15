# -*- coding: utf-8 -*-
"""B-541: como Fusion, un Enter acepta Empalme, Extruir y Patrón con el foco en la vista o en un campo del panel, una
sola vez (Enter en la caja de valor del asa ya aceptaba desde B-468). Eventos simulados, nunca el cursor real."""
import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from test_b468_caja_de_valor_como_fusion import _caso, _panel


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _abrir(nombre):
    if nombre != "patron":
        doc, comando, valores, _ = _caso(nombre)
        if nombre == "extruir":
            valores["distancia"] = "10 mm"
        return _panel(comando, doc, valores)
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc, *_ = _caso("empalme")
    valores = {"cuerpos": [hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)],
               "dir1": [hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)]}
    return _panel(CATALOGO["patron_rectangular_3d"](), doc, valores)


@pytest.mark.parametrize("nombre", ["empalme", "extruir", "patron"])
@pytest.mark.parametrize("foco", ["vista", "panel", "caja"])
def test_un_enter_acepta_una_sola_vez(app_qt, nombre, foco):
    panel, visor = _abrir(nombre)
    panel._calcular_previa()
    aceptados = []
    panel.confirmar = lambda op: aceptados.append(op) or True
    if foco == "vista":
        visor.setFocus()
        QCoreApplication.processEvents()
        QCoreApplication.sendEvent(visor, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
    elif foco == "panel":
        campo = next(w for c, w in panel.widgets.items() if hasattr(w, "setText") and w.isVisible())
        campo.setFocus()
        QTest.keyClick(campo, Qt.Key_Return)
    else:
        caja = next(iter(panel.manipuladores.cajas.values()))
        caja.setFocus()
        QTest.keyClick(caja, Qt.Key_Return)
    QCoreApplication.processEvents()
    assert len(aceptados) == 1 and aceptados[0] is not None and not panel.isVisible()


def test_enter_en_la_vista_con_aceptar_apagado_no_acepta(app_qt):
    panel, visor = _abrir("extruir")
    panel._calcular_previa()
    panel.confirmar = lambda op: pytest.fail("no debía aceptar")
    panel.boton_ok.setEnabled(False)
    visor.setFocus()
    QCoreApplication.sendEvent(visor, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
    assert panel.isVisible()
    panel.cancelar()
