# -*- coding: utf-8 -*-
"""CF-8: las opciones de Preferencias › General que se fueron haciendo (C11 y C13). Lo que falte sigue abierto en
docs/seguimiento/faltantes.md.

La ayuda de Fusion:
- «Spacebar Repeats Last Command» (fusion-releasenotes: «Spacebar now activates Repeat Command»; y «disabling the
  'Spacebar Repeats Last Command' preference…» deja la barra espaciadora libre para otra asignación).
- «ViewCube Size» (fusion-getstarted/viewcube-reference): en el menú del clic derecho del ViewCube, con las opciones
  Automatic, Large, Normal, Small y Tiny.
- «UI Themes» (fusion-releasenotes/2025: «allows you to switch between Dark Blue, Match Device Theme, Light Gray and
  Fusion Classic»): «Match Device Theme» sigue al claro/oscuro del sistema.
- «Mouse setup (pan, zoom, orbit)» (fusion-getstarted/fusion-preferences-reference): los presets Alias, Inventor,
  PowerMill y SolidWorks con su zoom, encuadre y órbita.
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


def test_tema_del_sistema_sigue_al_claro_oscuro_de_windows(ventana, monkeypatch):
    """«Tema del sistema» (el «Match Device Theme» de Fusion) toma el claro o el oscuro que tiene el sistema, y lo
    sigue sin reiniciar cuando el sistema cambia."""
    from omnicad.ui import preferencias as pr
    from omnicad.ui import temas
    assert "sistema" in [clave for clave, _nombre, _propio in temas.disponibles()[0]]
    try:
        ventana.prefs["general/tema"] = "sistema"
        monkeypatch.setattr(temas, "esquema_sistema", lambda: "claro")
        ventana.aplicar_tema()
        assert temas.clave_activa() == "sistema" and temas.nombre_activo() == "Tema del sistema"
        assert temas.color("fondo") == temas.INCLUIDOS["claro_moderno"]["colores"]["fondo"]
        monkeypatch.setattr(temas, "esquema_sistema", lambda: "oscuro")
        ventana.aplicar_tema()
        assert temas.color("fondo") == temas.INCLUIDOS["oscuro_moderno"]["colores"]["fondo"]
        combo = pr._combo_temas("sistema")             # el combo de Preferencias › General lo ofrece y lo deja elegido
        assert combo.currentData() == "sistema" and combo.itemText(0) == "Tema del sistema"
        from omnicad.api.herramientas_preferencias import _OPCIONES
        assert "general/tema" not in _OPCIONES         # el tema no le sirve a un agente (CLAUDE.md, brechas_mcp.md)
    finally:
        ventana.prefs["general/tema"] = "oscuro_moderno"
        ventana.aplicar_tema()


def test_raton_estilos_alias_inventor_powermill_solidworks(ventana):
    """Los presets de ratón de Fusion, con su zoom, encuadre y órbita (la rueda sigue haciendo zoom en todos: sin eso
    el ratón parecería roto)."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.ui import preferencias as pr
    v, c = ventana.visor, ventana.visor.config
    original, v.modo = c.esquema_raton, None
    try:
        c.esquema_raton = "alias"                      # Mayús+Alt: izquierdo órbita, medio encuadre, derecho zoom
        assert v.accion_raton(Qt.LeftButton, Qt.ShiftModifier | Qt.AltModifier) == "orbita"
        assert v.accion_raton(Qt.MiddleButton, Qt.ShiftModifier | Qt.AltModifier) == "encuadre"
        assert v.accion_raton(Qt.RightButton, Qt.ShiftModifier | Qt.AltModifier) == "zoom"
        assert v.accion_raton(Qt.LeftButton, Qt.NoModifier) is None     # sin Mayús+Alt, el izquierdo selecciona
        c.esquema_raton = "powermill"                  # medio órbita, Mayús+medio encuadre
        assert v.accion_raton(Qt.MiddleButton, Qt.NoModifier) == "orbita"
        assert v.accion_raton(Qt.MiddleButton, Qt.ShiftModifier) == "encuadre"
        c.esquema_raton = "solidworks"                 # medio órbita, Ctrl+medio encuadre
        assert v.accion_raton(Qt.MiddleButton, Qt.NoModifier) == "orbita"
        assert v.accion_raton(Qt.MiddleButton, Qt.ControlModifier) == "encuadre"
        c.esquema_raton = "inventor"                   # F2 encuadre, F3 zoom, F4 órbita + arrastre izquierdo
        assert v.accion_raton(Qt.MiddleButton, Qt.NoModifier) == "encuadre"
        QTest.keyPress(v, Qt.Key_F3)
        try:
            assert v.accion_raton(Qt.LeftButton, Qt.NoModifier) == "zoom"
        finally:
            QTest.keyRelease(v, Qt.Key_F3)
        assert v.accion_raton(Qt.LeftButton, Qt.NoModifier) is None     # soltar la tecla lo devuelve a seleccionar
        atajo = QKeyEvent(QEvent.ShortcutOverride, Qt.Key_F2, Qt.NoModifier)
        QApplication.sendEvent(v, atajo)
        assert atajo.isAccepted()                      # con Inventor, F2 navega en el visor y no dispara Renombrar
        c.esquema_raton = "fusion"
        atajo = QKeyEvent(QEvent.ShortcutOverride, Qt.Key_F2, Qt.NoModifier)
        atajo.ignore()
        QApplication.sendEvent(v, atajo)
        assert not atajo.isAccepted()                  # con los demás estilos, F2 sigue siendo Renombrar
        QTest.keyPress(v, Qt.Key_F3)
        assert v._tecla_nav is None
        QTest.keyRelease(v, Qt.Key_F3)
    finally:
        c.esquema_raton = original
    opciones = [clave for _pag, _pad, _tit, _desc, filas in pr.PAGINAS for f in filas
                if f[0] == "general/raton" for clave, _texto in f[3]]
    assert opciones == ["omnicad", "fusion", "alias", "inventor", "powermill", "solidworks", "tinkercad"]
    from omnicad.api.herramientas_preferencias import _OPCIONES
    assert _OPCIONES["general/raton"] == ("fusion", opciones)
