"""B-581: en Extruir, Aceptar abre siempre en el mismo lugar y un aviso no lo empuja, ni siquiera el que llega antes
de que el panel se asiente (E11 lo vio a 488/500/516/540 px según los avisos y erraba el clic)."""
from PySide6.QtTest import QTest

from omnicad.ui.comandos import CATALOGO
from test_b421_botones_no_se_mueven import _centros, ventana  # noqa: F401 — fixture


def test_b581_aceptar_queda_en_el_mismo_lugar_con_y_sin_aviso(ventana):  # noqa: F811
    lugares = []
    for aviso in ("", "Aviso corto.", "Un aviso largo que ocupa varios renglones del panel. " * 4):
        panel = ventana.ejecutar_comando(CATALOGO["extruir"]())
        lugares.append(_centros(panel))
        if aviso:
            panel._mostrar(aviso, tipo="aviso")     # apenas abre: antes de que el pie se asiente
        QTest.qWait(400)
        lugares.append(_centros(panel))
        panel._mostrar("")                          # el aviso se va
        QTest.qWait(120)
        lugares.append(_centros(panel))
        panel.cancelar()
        QTest.qWait(50)
    assert all(lugar == lugares[0] for lugar in lugares), lugares
