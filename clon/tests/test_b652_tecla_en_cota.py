# -*- coding: utf-8 -*-
"""B-652: con una cota elegida, teclear un número la edita (antes los números iban a los atajos de la ventana y
cerraban el boceto)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence  # noqa: E402
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


def test_b831_cota_no_dispara_atajos_y_recupera_el_campo(app_qt):
    lz = T._lienzo(app_qt, Boceto())
    lz.b.agregar_circulo((0, 0), 30.996)
    lz.activateWindow()
    lz.setFocus()
    QTest.qWait(1)
    atajo = QAction("Aspecto", lz)
    atajo.setShortcut(QKeySequence("A"))
    lz.addAction(atajo)
    disparos = []
    atajo.triggered.connect(lambda: disparos.append(True))
    lz.set_herramienta("cota")
    ev = QKeyEvent(QEvent.ShortcutOverride, Qt.Key_A, Qt.NoModifier, "a")
    lz.event(ev)
    assert ev.isAccepted()
    QTest.keyClicks(lz, "a")
    assert not disparos and lz.entrada is None
    T._clic(lz, 0, 30.996)
    assert lz.entrada is not None
    campo = lz.entrada.campos[0]
    lz.setFocus()                         # el clic dejó el teclado en el lienzo
    QTest.keyClicks(lz, "a")
    assert not disparos and campo.text() == "a"
    QTest.keyClicks(campo, "2")
    assert campo.text() == "a2" and lz.herramienta == "cota"
