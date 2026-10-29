# -*- coding: utf-8 -*-
"""Arnés de pruebas de UI: el modo de ventana (`OMNICAD_PRUEBA_VENTANA`) de `scripts/prueba_ui/arnes.py`."""
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "prueba_ui"))
_excepthook = sys.excepthook
import arnes as A  # noqa: E402  (instala un gancho de excepciones propio: se devuelve el de pytest)

sys.excepthook = _excepthook


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_modo_por_defecto_es_visible(monkeypatch):
    monkeypatch.delenv("OMNICAD_PRUEBA_VENTANA", raising=False)
    assert A.modo_ventana() == "visible"


def test_modo_invalido_falla(monkeypatch):
    monkeypatch.setenv("OMNICAD_PRUEBA_VENTANA", "oculta")
    with pytest.raises(ValueError):
        A.modo_ventana()


def test_minimizada_es_transparente_sin_foco_y_queda_activa_para_los_atajos(monkeypatch, app):
    monkeypatch.setenv("OMNICAD_PRUEBA_VENTANA", "minimizada")
    w = QWidget()
    A.mostrar(w)
    A.activar(w)
    assert w.testAttribute(Qt.WA_ShowWithoutActivating)
    assert w.isVisible() and w.windowOpacity() == 0.0
    assert w.windowFlags() & Qt.WindowDoesNotAcceptFocus
    assert QApplication.activeWindow() is w
    w.close()


def test_visible_se_muestra_normal(monkeypatch, app):
    monkeypatch.setenv("OMNICAD_PRUEBA_VENTANA", "visible")
    w = QWidget()
    A.mostrar(w)
    assert w.isVisible() and not w.isMinimized()
    assert not w.testAttribute(Qt.WA_ShowWithoutActivating)
    w.close()

