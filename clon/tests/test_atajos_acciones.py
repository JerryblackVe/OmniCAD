# -*- coding: utf-8 -*-
"""Atajos de las acciones de la ventana (B-104): la ayuda no puede quedar en el lugar del atajo."""
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
    carpeta = tmp_path_factory.mktemp("atajos")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def test_recuperar_documentos_sin_atajo_y_con_su_ayuda(ventana):
    a = ventana.acciones["recuperados"]
    assert a.shortcut().isEmpty()
    assert "Documentos recuperados" in a.property("ayuda")
    assert "Abre «Documentos recuperados»" in a.toolTip()


def test_ninguna_accion_tiene_un_texto_de_ayuda_como_atajo(ventana):
    raros = {c: a.shortcut().toString() for c, a in ventana.acciones.items()
             if len(a.shortcut().toString()) > 25}
    assert raros == {}
