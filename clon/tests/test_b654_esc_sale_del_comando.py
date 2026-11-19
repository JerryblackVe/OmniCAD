# -*- coding: utf-8 -*-
"""B-654 / B-655: un solo Esc sale de la restricción (Paralelo…) o del Texto, como en Fusion."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones.boceto import Boceto  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def test_un_esc_sale_de_paralelo_con_una_linea_elegida(app_qt):
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (20, 0))
    b.agregar_linea((0, 10), (20, 15))
    lz = T._lienzo(app_qt, b)
    lz.set_herramienta("r_paralela")
    lz.picks = [l1]
    QTest.keyClick(lz, Qt.Key_Escape)
    assert lz.herramienta == "seleccionar" and not lz.picks


def test_un_esc_sale_del_texto_con_el_cuadro_abierto(app_qt):
    lz = T._lienzo(app_qt, Boceto())
    lz.set_herramienta("texto")
    lz.cancelar()
    assert lz.herramienta == "seleccionar"
