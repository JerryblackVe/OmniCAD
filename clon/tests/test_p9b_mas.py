# -*- coding: utf-8 -*-
"""P9 (segunda tanda): botón «Más» (⋮) de los comandos de los menús de la cinta: Fijar en atajos, Fijar en la barra
y Cambiar atajo de teclado (`ui/mas_comando.py`)."""
import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMenu, QToolButton  # noqa: E402

from omnicad.ui.caja_herramientas import leer_fijados  # noqa: E402
from omnicad.ui.mas_comando import DialogoAtajo, alternar, conflicto, leer_barra, leer_teclas  # noqa: E402
from omnicad.ui.preferencias import Preferencias  # noqa: E402
from omnicad.ui.ventana import VentanaPrincipal  # noqa: E402


@pytest.fixture
def ini(tmp_path):
    return str(tmp_path / "p.ini")


def _ventana(ini):
    QApplication.instance() or QApplication([])
    v = VentanaPrincipal(prefs=Preferencias(QSettings(ini, QSettings.IniFormat)))
    v.show()
    QTest.qWait(30)
    return v


def _cerrar(v):
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


@pytest.fixture
def v(ini):
    ventana = _ventana(ini)
    yield ventana
    _cerrar(ventana)


def _menu_de(v, clave):
    return next(m for m in v.findChildren(QMenu) if v.acciones[clave] in m.actions())


def test_alternar_agrega_al_final_o_quita():
    assert alternar(["a", "b"], "c") == ["a", "b", "c"] and alternar(["a", "b"], "a") == ["b"]


def test_solo_los_comandos_reales_tienen_mas(v):
    f = v._filtro_mas
    assert f.clave(v.acciones["extruir"]) == "extruir" and f.clave(v.acciones["vaciado"]) == "vaciado"
    assert f.clave(None) is None
    menu = next(m for m in v.findChildren(QMenu)          # el menú CREAR: tiene el submenú «Patrón»
                if v.acciones["extruir"] in m.actions() and any(a.menu() for a in m.actions()))
    sub = next(a for a in menu.actions() if a.menu() is not None)
    assert f.clave(sub) is None                                   # un submenú no es un comando
    assert all(f.clave(a) is None for a in v.cinta.no_disponibles)    # lo no disponible no tiene «Más»


def test_clic_en_el_mas_abre_el_menu_y_no_ejecuta_el_comando(v):
    menu = _menu_de(v, "extruir")
    menu.popup(QPoint(40, 40))
    QTest.qWait(30)
    accion = v.acciones["extruir"]
    zona = v._filtro_mas.zona(menu, accion)
    assert menu.actionGeometry(accion).contains(zona) and zona.width() == 22
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, zona.center())
    mas = v._filtro_mas.menu_abierto
    assert [a.text() for a in mas.actions() if a.text()] == ["Quitar de atajos", "Fijar en la barra",
                                                           "Cambiar atajo de teclado…"]
    assert v.panel is None                                        # no se abrió el diálogo de Extruir
    mas.hide()
    menu.hide()


def test_un_clic_fuera_del_mas_sigue_ejecutando_el_comando(v):
    menu = _menu_de(v, "caja")
    menu.popup(QPoint(40, 40))
    QTest.qWait(30)
    fila = menu.actionGeometry(v.acciones["caja"])
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, QPoint(fila.left() + 30, fila.center().y()))
    QTest.qWait(30)
    assert v.panel is not None
    v.panel.close()


def test_fijar_en_atajos_usa_la_lista_del_contexto_y_quita_lo_ya_fijado(v):
    assert leer_fijados(v.prefs, "diseno") == ["extruir", "empalme_3d"]
    assert v._filtro_mas.alternar_atajo("vaciado") == "diseno"
    assert leer_fijados(v.prefs, "diseno") == ["extruir", "empalme_3d", "vaciado"]
    v._filtro_mas.alternar_atajo("extruir")
    assert leer_fijados(v.prefs, "diseno") == ["empalme_3d", "vaciado"]
    assert leer_fijados(v.prefs, "boceto") == []


def test_fijar_en_la_barra_agrega_el_boton_y_al_reabrir_sigue_ahi(ini):
    v1 = _ventana(ini)
    assert v1._lay_fijados.count() == 0
    v1._filtro_mas.alternar_barra("vaciado")
    boton = v1._lay_fijados.itemAt(0).widget()
    assert isinstance(boton, QToolButton) and boton.defaultAction() is v1.acciones["vaciado"]
    _cerrar(v1)
    v2 = _ventana(ini)
    assert leer_barra(v2.prefs) == ["vaciado"] and v2._lay_fijados.count() == 1
    v2._filtro_mas.alternar_barra("vaciado")
    QTest.qWait(10)
    assert v2._lay_fijados.count() == 0 and leer_barra(v2.prefs) == []
    _cerrar(v2)


def test_cambiar_el_atajo_se_aplica_en_el_acto_y_se_guarda(ini):
    v1 = _ventana(ini)
    a = v1.acciones["vaciado"]
    assert a.shortcut().isEmpty()
    assert v1._filtro_mas.cambiar_tecla("vaciado", "Ctrl+Alt+V") == "Ctrl+Alt+V"
    assert a.shortcut() == QKeySequence("Ctrl+Alt+V") and "Alt" in a.text().split("\t")[1]
    assert "Alt" in a.toolTip() and json.loads(v1.prefs["atajos/teclas"]) == {"vaciado": "Ctrl+Alt+V"}
    _cerrar(v1)
    v2 = _ventana(ini)                                            # al reabrir, sigue
    assert v2.acciones["vaciado"].shortcut() == QKeySequence("Ctrl+Alt+V")
    _cerrar(v2)


def test_no_deja_repetir_el_atajo_de_otro_comando(v):
    assert v.acciones["deshacer"].shortcut() == QKeySequence("Ctrl+Z")
    assert conflicto(v.acciones, "vaciado", "Ctrl+Z") == "Deshacer"
    assert v._filtro_mas.cambiar_tecla("vaciado", "Ctrl+Z") is None
    assert v.acciones["vaciado"].shortcut().isEmpty() and leer_teclas(v.prefs) == {}


def test_volver_al_atajo_de_fabrica_borra_la_eleccion(v):
    a = v.acciones["extruir"]
    defecto = a.property("atajo_defecto")
    assert defecto == "E"
    v._filtro_mas.cambiar_tecla("extruir", "Ctrl+Alt+E")
    assert a.shortcut() == QKeySequence("Ctrl+Alt+E")
    v._filtro_mas.cambiar_tecla("extruir", defecto)
    assert a.shortcut() == QKeySequence("E") and leer_teclas(v.prefs) == {}
    v._filtro_mas.cambiar_tecla("extruir", "")                    # «Sin atajo»
    assert a.shortcut().isEmpty() and leer_teclas(v.prefs) == {"extruir": ""}


def test_un_json_roto_de_teclas_no_rompe_la_ventana(ini):
    QApplication.instance() or QApplication([])
    prefs = Preferencias(QSettings(ini, QSettings.IniFormat))
    prefs["atajos/teclas"] = "no es json"
    assert leer_teclas(prefs) == {}
    prefs["atajos/teclas"] = "[1, 2]"
    assert leer_teclas(prefs) == {}


def test_el_dialogo_avisa_del_conflicto_y_bloquea_aceptar(v):
    dlg = DialogoAtajo("Vaciado", "", "", lambda s: conflicto(v.acciones, "vaciado", s), v)
    ok = dlg.botones.button(QDialogButtonBox.Ok)
    assert ok.isEnabled() and dlg.aviso.text() == ""
    dlg.editor.setKeySequence(QKeySequence("Ctrl+Z"))
    assert not ok.isEnabled() and "Deshacer" in dlg.aviso.text()
    dlg.editor.setKeySequence(QKeySequence("Ctrl+Alt+V"))
    assert ok.isEnabled() and dlg.secuencia() == "Ctrl+Alt+V"
    dlg.restablecer.click()
    assert dlg.secuencia() == ""
    dlg.deleteLater()
