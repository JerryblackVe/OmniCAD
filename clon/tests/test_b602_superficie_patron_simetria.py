# -*- coding: utf-8 -*-
"""B-602: SUPERFICIE › CREAR ofrece Patrón y Simetría, como en Fusion."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad.ui.cinta import Cinta  # noqa: E402

SUPERFICIE = 1


class _Acciones(dict):
    def __missing__(self, clave):
        accion = QAction(clave.replace("_", " ").capitalize())
        self[clave] = accion
        return accion


@pytest.fixture
def cinta():
    app = QApplication.instance() or QApplication([])
    c = Cinta(_Acciones())
    c.resize(1200, 160)
    c.show()
    QTest.qWaitForWindowExposed(c)
    yield c
    c.close()
    c.deleteLater()
    app.processEvents()


def _grupo_crear(c):
    pagina = c.pila.currentWidget()
    return next(b for b in pagina.findChildren(QToolButton, "titulo_grupo") if b.toolTip() == "CREAR")


def _abrir(c):
    grupo = _grupo_crear(c)
    QTest.mouseClick(grupo, Qt.LeftButton)
    assert grupo.menu().isVisible()
    return grupo.menu()


def _clic(menu, accion):
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, menu.actionGeometry(accion).center())


def test_patron_y_simetria_se_abren_desde_superficie_crear(cinta):
    QTest.mouseClick(cinta.pestanas[SUPERFICIE], Qt.LeftButton)
    menu = _abrir(cinta)
    patron = next((a for a in menu.actions() if a.text() == "Patrón" and a.menu()), None)
    assert patron is not None, "SUPERFICIE › CREAR no tiene Patrón"
    assert cinta.acciones["patron_circular_3d"] in patron.menu().actions()

    abiertos = []
    cinta.acciones["patron_circular_3d"].triggered.connect(lambda _=False: abiertos.append("patrón"))
    _clic(menu, patron)
    QTest.keyClick(menu, Qt.Key_Right)
    assert patron.menu().isVisible()
    _clic(patron.menu(), cinta.acciones["patron_circular_3d"])
    assert abiertos == ["patrón"]

    menu = _abrir(cinta)
    simetria = cinta.acciones["simetria_3d"]
    assert simetria in menu.actions()
    simetria.triggered.connect(lambda _=False: abiertos.append("simetría"))
    _clic(menu, simetria)
    assert abiertos == ["patrón", "simetría"]
