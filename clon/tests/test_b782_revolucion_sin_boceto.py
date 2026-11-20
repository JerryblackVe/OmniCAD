# -*- coding: utf-8 -*-
"""B-782: Revolución sin boceto abre el panel con un aviso de 1 renglón, sin cuadro modal (como Fusion)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_revolucion_sin_boceto_abre_el_panel_con_aviso_adentro(monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
    from omnicad.ui.comandos.solido import Revolucion
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: (_ for _ in ()).throw(AssertionError("modal")))
    v = VentanaPrincipal()
    p = v.ejecutar_comando(Revolucion())
    assert p is not None
    QTest.qWait(100)
    assert any("Primero creá un boceto" in l.text() for l in p.findChildren(QLabel))
    p.cancelar()
    v.close()
    del app
