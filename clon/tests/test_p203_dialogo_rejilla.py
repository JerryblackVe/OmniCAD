# -*- coding: utf-8 -*-
"""P-203: Parámetros de rejilla: con «Adaptativa» los campos de la fija quedan en gris, y teclear de más avisa el máximo."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def test_p203_adaptativa_en_gris_y_aviso_del_maximo():
    QApplication.instance() or QApplication([])
    from omnicad.ui.dialogos import DialogoRejilla
    dlg = DialogoRejilla()
    assert dlg.adaptativa.isChecked() and not dlg.espaciado.isEnabled() and not dlg.subdivisiones.isEnabled()
    dlg.fija.setChecked(True)
    assert dlg.espaciado.isEnabled() and dlg.subdivisiones.isEnabled()
    dlg.subdivisiones.lineEdit().selectAll()
    QTest.keyClicks(dlg.subdivisiones.lineEdit(), "99999")
    assert dlg.aviso.text() == "⚠ Máximo 1000"
    dlg.espaciado.lineEdit().selectAll()
    QTest.keyClicks(dlg.espaciado.lineEdit(), "1e9")
    QTest.keyClicks(dlg.espaciado.lineEdit(), "9999999")
    assert dlg.aviso.text() == "⚠ Máximo 100000 mm"
    dlg.subdivisiones.setValue(5)
    assert dlg.valor() == (dlg.espaciado.value(), 5) and isinstance(dlg.valor()[1], int)
    assert DialogoRejilla((20.0, 4)).valor() == (20.0, 4)
