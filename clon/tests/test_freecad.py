# -*- coding: utf-8 -*-
"""F16 (FreeCAD 1.0: pulidos de uso): buscador dentro de Preferencias. La detección de restricciones
en conflicto (F5) y las demás brechas F van en su momento; esto es lo hecho en esta tanda."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


def _dlg(tmp_path):
    from omnicad.ui.preferencias import DialogoPreferencias, Preferencias
    prefs = Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    return DialogoPreferencias(prefs)


def test_buscador_de_preferencias_encuentra_por_etiqueta(app_qt, tmp_path):
    dlg = _dlg(tmp_path)
    try:
        dlg.buscar.setText("autoguardado")               # una etiqueta de la página General
        assert not dlg._items["general"].isDisabled()
        assert dlg.arbol.currentItem() is dlg._items["general"]   # salta a la primera coincidencia
        dlg.buscar.setText("zzz-nada")                   # nada: todas atenuadas, sin saltar
        assert all(it.isDisabled() for it in dlg._items.values())
        dlg.buscar.setText("")                           # vacío: todo habilitado otra vez
        assert not any(it.isDisabled() for it in dlg._items.values())
        dlg.buscar.setText("gráficos")                    # busca en el título de la página
        assert not dlg._items["graficos"].isDisabled()
    finally:
        dlg.reject()
