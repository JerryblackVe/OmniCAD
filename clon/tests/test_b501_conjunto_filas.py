# -*- coding: utf-8 -*-
"""B-501: en ENSAMBLAR › Conjunto, el nombre y el desfase tecleados en las cajas de la fila guardada llegan a la fila
(teclear y Tab con eventos simulados, nunca el cursor real)."""
import os


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from test_posicion_ventana import ventana  # noqa: E402,F401  (la fixture: ventana con dos componentes)

from omnicad.ui.comandos.ensamblar import RestriccionComponentes  # noqa: E402

FILA = {"tipo": "alinear", "ref1": [{"tipo": "cara"}], "ref2": [{"tipo": "cara"}], "desfase": "5 mm", "nombre_fila": ""}


def _teclear(caja, texto):
    caja.setFocus()
    caja.selectAll()
    QTest.keyClicks(caja, texto)
    QTest.keyClick(caja, Qt.Key_Tab)          # Tab termina la edición (Enter aceptaría todo el panel)


def test_el_nombre_y_el_desfase_tecleados_llegan_a_la_fila_guardada(ventana):  # noqa: F811
    v = ventana
    v.activateWindow()
    QTest.qWaitForWindowActive(v)
    p = v.ejecutar_comando(RestriccionComponentes())
    p.set_valores({"filas": [dict(FILA)]})
    p.comando._pintar_filas(p)
    assert p._lista_filas.count() == 1
    p._lista_filas.setCurrentRow(0)
    _teclear(p._edit_nombre, "frente")
    _teclear(p._edit_desfase, "7 mm")
    fila = p.valores["filas"][0]
    assert fila["nombre_fila"] == "frente" and fila["desfase"] == "7 mm"
    assert p._lista_filas.item(0).text().startswith("1. frente")
    assert p._edit_nombre.text() == "frente" and p._edit_desfase.text() == "7 mm"      # y las cajas lo siguen mostrando
    p.cancelar()


def test_lo_tecleado_queda_en_la_fila_sin_soltar_el_foco(ventana):  # noqa: F811
    """Aunque la caja no pierda el foco (ventana inactiva, Mac sin foco en botones), lo escrito ya está en la fila."""
    p = ventana.ejecutar_comando(RestriccionComponentes())
    p.set_valores({"filas": [dict(FILA)]})
    p.comando._pintar_filas(p)
    p._lista_filas.setCurrentRow(0)
    for caja, texto in ((p._edit_nombre, "frente"), (p._edit_desfase, "9 mm")):
        caja.setFocus()
        caja.selectAll()
        QTest.keyClicks(caja, texto)                      # sin Tab
    fila = p.valores["filas"][0]
    assert fila["nombre_fila"] == "frente" and fila["desfase"] == "9 mm"
    assert p._lista_filas.item(0).text().startswith("1. frente")
    assert p._edit_nombre.text() == "frente"              # el cursor no saltó: la caja conserva lo escrito
    p.cancelar()
