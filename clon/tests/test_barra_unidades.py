# -*- coding: utf-8 -*-
"""«Unidades: mm, g ▾» en la barra de abajo (ui/panel_timeline.py + ventana._crear_menu_unidades)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad.ui import formato  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("unidades")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def _acciones(menu):
    return {a.text(): a for a in menu.actions() if a.text()}


def test_boton_y_unidades_actuales(ventana):
    assert ventana.timeline.unidades.text().startswith("Unidades: mm, g")
    acciones = _acciones(ventana.menu_unidades)
    assert acciones["Milímetro (mm)"].isChecked() and acciones["Milímetro (mm)"].isEnabled()
    assert acciones["Gramo (g)"].isChecked() and acciones["Gramo (g)"].isEnabled()


def test_las_unidades_no_implementadas_estan_grisadas_y_explican_por_que(ventana):
    acciones = _acciones(ventana.menu_unidades)
    for texto in ("Centímetro (cm)", "Metro (m)", "Pulgada (in)", "Pie (ft)", "Kilogramo (kg)", "Libra (lb)"):
        assert not acciones[texto].isEnabled() and "No disponible" in acciones[texto].toolTip()
    assert "2 in" in acciones["Pulgada (in)"].toolTip()


def test_elegir_precision_la_guarda_y_la_aplica(ventana):
    ventana.menu_unidades.aboutToShow.emit()
    precision = next(a.menu() for a in ventana.menu_unidades.actions() if a.text() == "Precisión")
    marcada = [a.data() for a in precision.actions() if a.isChecked()]
    assert marcada == [ventana.prefs["unidades/precision"]]
    try:
        next(a for a in precision.actions() if a.data() == 1).trigger()
        assert ventana.prefs["unidades/precision"] == 1
        assert formato.numero(12.3456) == "12.3"
    finally:
        ventana._pref_unidades("unidades/precision", 3)
    assert formato.numero(12.3456) == "12.346"


def test_preferencias_abre_en_la_pagina_pedida(ventana):
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(ventana.prefs, ventana, "valores")
    assert dlg.arbol.currentItem().text(0) == "Visualización de unidad y valor"
    dlg.deleteLater()
    dlg = DialogoPreferencias(ventana.prefs, ventana, "no_existe")
    assert dlg.arbol.currentItem().text(0) == "General"
    dlg.deleteLater()
