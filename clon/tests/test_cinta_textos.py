# -*- coding: utf-8 -*-
"""Texto bajo los íconos de la cinta (ui/cinta.py): la etiqueta de cada botón y el paso a «solo ícono» cuando la
pestaña no entra a lo ancho."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad.ui.cinta import ANCHO_SOLO_ICONO, Cinta, etiqueta_boton  # noqa: E402


def test_etiqueta_sin_atajo_ni_puntos_y_siempre_en_dos_renglones():
    assert etiqueta_boton("Extruir\tE") == "Extruir\n "
    assert etiqueta_boton("Insertar STEP…") == "Insertar\nSTEP"
    assert etiqueta_boton("Crear boceto") == "Crear\nboceto"
    assert etiqueta_boton("Plano de desfase") == "Plano de\ndesfase"     # corta en el espacio más cercano al medio
    assert etiqueta_boton("Interferencia") == "Interferencia\n "         # largo pero sin espacios: un renglón


class _Acciones(dict):
    """Las acciones que la cinta pida, creadas al vuelo (la ventana real tiene una por clave)."""

    def __missing__(self, clave):
        a = QAction(clave.replace("_", " ").capitalize())
        self[clave] = a
        return a


@pytest.fixture
def cinta():
    QApplication.instance() or QApplication([])
    c = Cinta(_Acciones())
    c.resize(4000, 160)
    c.show()
    QTest.qWaitForWindowExposed(c)
    yield c
    c.close()
    c.deleteLater()


def _botones(c):
    return c.pila.currentWidget().findChildren(QToolButton, "boton_cinta")


def test_con_lugar_hay_texto_y_sin_lugar_solo_icono(cinta):
    assert all(b.toolButtonStyle() == Qt.ToolButtonTextUnderIcon for b in _botones(cinta))
    cinta.resize(500, 160)
    QTest.qWait(10)
    assert all(b.toolButtonStyle() == Qt.ToolButtonIconOnly and b.width() == ANCHO_SOLO_ICONO for b in _botones(cinta))
    cinta.resize(4000, 160)
    QTest.qWait(10)
    assert all(b.toolButtonStyle() == Qt.ToolButtonTextUnderIcon for b in _botones(cinta))


def test_cambiar_de_pestana_ajusta_la_nueva(cinta):
    cinta.resize(500, 160)
    QTest.qWait(10)
    cinta.pestanas[3].click()                   # CHAPA
    assert cinta.pestana_actual() == "CHAPA"
    assert _botones(cinta) and all(b.toolButtonStyle() == Qt.ToolButtonIconOnly for b in _botones(cinta))


def test_los_menus_siguen_con_el_nombre_completo(cinta):
    a = cinta.acciones["extruir"]
    assert a.text() == "Extruir" and a.iconText() == "Extruir\n "
