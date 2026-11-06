# -*- coding: utf-8 -*-
"""CF-8 (tanda C11): las dos opciones de Preferencias que se hicieron — la barra espaciadora que repite el último
comando y el tamaño del ViewCube. El resto de las opciones de CF-8 sigue abierto en docs/seguimiento/faltantes.md.

La ayuda de Fusion:
- «Spacebar Repeats Last Command» (fusion-releasenotes: «Spacebar now activates Repeat Command»; y «disabling the
  'Spacebar Repeats Last Command' preference…» deja la barra espaciadora libre para otra asignación).
- «ViewCube Size» (fusion-getstarted/viewcube-reference): en el menú del clic derecho del ViewCube, con las opciones
  Automatic, Large, Normal, Small y Tiny.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("preferencias")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def test_barra_espaciadora_repite_el_ultimo_comando(ventana):
    """Apagada (de fábrica) la barra espaciadora sigue siendo «Boceto sobre la cara elegida» (PL3); encendida repite
    el último comando, como Fusion, y deja de ser de «Boceto sobre la cara» (es el otro extremo del mismo ajuste)."""
    ventana.prefs["general/espacio_repite"] = False
    ventana.aplicar_teclas()
    assert ventana.acciones["boceto_cara"].shortcut().toString() == "Space"
    assert ventana.acciones["repetir"].shortcut().toString() == "Shift+R"

    ventana.prefs["general/espacio_repite"] = True
    ventana.aplicar_teclas()
    assert ventana.acciones["repetir"].shortcut().toString() == "Space"
    assert ventana.acciones["boceto_cara"].shortcut().isEmpty()
    try:
        # y de verdad repite: con la barra espaciadora vuelve a abrir el último comando
        from PySide6.QtTest import QTest

        from omnicad.ui.comandos import CATALOGO
        hechos, original = [], ventana.ejecutar_comando
        ventana.ejecutar_comando = lambda c: hechos.append(type(c).__name__)
        ventana._ultimo_comando = CATALOGO["caja"]
        try:
            ventana.activateWindow()
            QTest.qWait(20)                     # sin la ventana activa, Qt no reparte los atajos
            QTest.keyClick(ventana.area, Qt.Key_Space)
        finally:
            ventana.ejecutar_comando = original
            ventana._ultimo_comando = None
        assert hechos == [CATALOGO["caja"].__name__]
    finally:
        ventana.prefs["general/espacio_repite"] = False
        ventana.aplicar_teclas()


def test_tamano_del_viewcube_como_fusion(ventana):
    """El tamaño se elige en el menú del clic derecho del ViewCube, con las cinco opciones de Fusion, y queda guardado
    en las preferencias (también está en Preferencias › General y en la API, con los mismos cinco valores)."""
    vc = ventana.area.viewcube
    ventana.prefs["general/tamano_viewcube"] = "automatico"
    vc.set_tamano("automatico")
    automatico = vc.width()
    menu = vc.menu_tamano()
    assert [a.text() for a in menu.actions()] == ["Automático", "Grande", "Normal", "Pequeño", "Diminuto"]
    assert [a.text() for a in menu.actions() if a.isChecked()] == ["Automático"]

    menu.actions()[1].trigger()                     # Grande
    assert vc.width() > automatico
    assert ventana.prefs["general/tamano_viewcube"] == "grande"
    assert [a.text() for a in vc.menu_tamano().actions() if a.isChecked()] == ["Grande"]

    vc.menu_tamano().actions()[4].trigger()         # Diminuto
    assert vc.width() < automatico

    from omnicad.ui import preferencias as pr
    opciones = [clave for _pag, _pad, _tit, _desc, filas in pr.PAGINAS for f in filas
                if f[0] == "general/tamano_viewcube" for clave, _texto in f[3]]
    assert opciones == ["automatico", "grande", "normal", "pequeno", "diminuto"]

    from omnicad.api.herramientas_preferencias import _OPCIONES
    assert _OPCIONES["general/tamano_viewcube"] == ("automatico", opciones)
    assert _OPCIONES["general/espacio_repite"] == (False, [False, True])
