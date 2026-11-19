# -*- coding: utf-8 -*-
"""B-689: con la caja de la espiral abierta, lo que se teclea con el foco en el Lienzo entra en «Vueltas»
y Enter crea la espiral (con lo escrito o con los valores por defecto, como Fusion)."""
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones.boceto import Boceto  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def _lienzos_con_caja(app_qt):
    """Espiral tras los 2 clics, con el foco en el Lienzo (como quedó en la prueba de la ventana real)."""
    lz = T._lienzo(app_qt, Boceto())
    lz.grab()
    lz.set_herramienta("espiral")
    T._clic(lz, 0, 0)
    T._clic(lz, 12, 0)
    assert lz.entrada is not None, "los 2 clics abren la caja de Vueltas/Paso"
    lz.setFocus()
    return lz


def _curva_unica(lz):
    curvas = [c for c in lz.b.curvas.values() if c.id > 0]
    assert len(curvas) == 1 and curvas[0].tipo == "spline", "la espiral no quedó creada"
    return curvas[0]


def _radio_final(lz):
    """Radio del último punto de ajuste de la espiral creada (r0 + vueltas · paso)."""
    return math.dist(lz.b.coords(_curva_unica(lz).pts[-1]), (0, 0))


def test_lo_tecleado_con_el_foco_en_el_lienzo_llega_a_vueltas(app_qt):
    lz = _lienzos_con_caja(app_qt)
    QTest.keyClick(lz, "5")
    assert lz.entrada.campos[0].text() == "5", "lo tecleado no llegó al campo de Vueltas"


def test_enter_en_el_lienzo_crea_la_espiral_con_lo_escrito(app_qt):
    lz = _lienzos_con_caja(app_qt)
    QTest.keyClick(lz, "5")
    QTest.keyClick(lz, Qt.Key_Return)
    assert lz.entrada is None, "la caja no se cerró al aceptar"
    assert _radio_final(lz) > 40                          # 5 vueltas: radio final 12 + 5·6


def test_enter_en_el_lienzo_crea_la_espiral_con_los_valores_por_defecto(app_qt):
    lz = _lienzos_con_caja(app_qt)
    QTest.keyClick(lz, Qt.Key_Return)
    assert 25 < _radio_final(lz) < 32                    # 3 vueltas por defecto: radio final 12 + 3·6


def test_el_numero_con_el_foco_en_el_lienzo_no_va_al_atajo_de_vista(app_qt):
    lz = _lienzos_con_caja(app_qt)
    ev = QKeyEvent(QEvent.ShortcutOverride, Qt.Key_3, Qt.NoModifier, "3")
    lz.event(ev)
    assert ev.isAccepted(), "el número se fue a los atajos de la ventana en vez de la caja"
