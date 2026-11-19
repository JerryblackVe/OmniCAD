# -*- coding: utf-8 -*-
"""B-652: con una cota elegida, teclear un número la edita (antes los números iban a los atajos de la ventana y
cerraban el boceto)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones.boceto import Boceto  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def test_teclear_con_una_cota_elegida_abre_su_caja(app_qt):
    b = Boceto()
    c = b.agregar_circulo((0, 0), 10)
    cid = b.agregar_cota("diametro", [c], "20")
    lz = T._lienzo(app_qt, b)
    lz.grab()
    lz.seleccion = [cid]
    ev = QKeyEvent(QEvent.ShortcutOverride, Qt.Key_2, Qt.NoModifier, "2")
    lz.event(ev)
    assert ev.isAccepted(), "el número no debe llegar a los atajos de la ventana"
    QTest.keyClick(lz, "2")
    assert lz.entrada is not None and lz.entrada.campos[0].text() == "2"
    for ch in "0*2+10":
        QTest.keyClick(lz.entrada.campos[0], ch)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert T._cotas(lz) == [("diametro", "20*2+10")]
