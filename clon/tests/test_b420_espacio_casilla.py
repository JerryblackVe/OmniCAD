# -*- coding: utf-8 -*-
"""B-420: con el foco en una casilla de un panel, la barra espaciadora la marca y no dispara el atajo global."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("b420")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    v.activateWindow()
    QTest.qWait(50)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def test_espacio_marca_la_casilla_y_no_abre_el_boceto(ventana):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from omnicad.ui.comandos import CATALOGO
    panel = ventana.ejecutar_comando(CATALOGO["rosca"]())
    QTest.qWait(50)
    casilla = panel.widgets["largo_completo"]
    disparos = []
    ventana.acciones["boceto_cara"].triggered.connect(lambda *_: disparos.append(1))
    assert ventana.acciones["boceto_cara"].shortcut().toString() == "Space"
    antes = casilla.isChecked()
    casilla.setFocus()
    QTest.qWait(20)
    QTest.keyClick(casilla, Qt.Key_Space)
    assert casilla.isChecked() != antes and disparos == []
    QTest.keyClick(casilla, Qt.Key_Space)
    assert casilla.isChecked() == antes and disparos == []
    panel.cancelar()


def test_espacio_sin_foco_en_un_boton_sigue_siendo_el_atajo(ventana):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication, QLabel
    etiqueta = QLabel("sin foco de botón", ventana)
    ev = QKeyEvent(QEvent.ShortcutOverride, Qt.Key_Space, Qt.NoModifier)
    ev.ignore()
    QApplication.sendEvent(etiqueta, ev)
    assert not ev.isAccepted()
