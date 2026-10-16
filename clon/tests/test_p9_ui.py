# -*- coding: utf-8 -*-
"""P9 (pulir la interfaz): la ayuda de los tooltips que se agregó y el aire de la cinta no se pierdan.
Regresión de la auditoría de scripts/auditoria_ui.py (hallazgos corregidos el 2026-10-16)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QHBoxLayout


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.show()
    QTest.qWait(50)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


def _ayuda(accion):
    """El tooltip trae ayuda: el título en negrita y una línea más debajo."""
    return accion.toolTip().count("<br>") >= 1


def test_las_acciones_de_vistas_y_paneles_explican_que_hacen(ventana):
    for clave in ("vista_iso", "vista_frente", "vista_arriba", "vista_derecha", "ejemplo", "acerca",
                  "ver_navegador", "ver_viewcube", "ver_barra_nav", "ver_timeline"):
        assert _ayuda(ventana.acciones[clave]), f"{clave} quedó sin ayuda: {ventana.acciones[clave].toolTip()!r}"


def test_la_prioridad_y_los_filtros_de_seleccion_explican_que_hacen(ventana):
    for clave in ("prioridad_cuerpo", "prioridad_cara", "prioridad_arista", "prioridad_componente",
                  "filtro_caras", "filtro_aristas", "filtro_vertices", "filtro_cuerpos", "filtro_bocetos",
                  "filtro_construccion"):
        assert _ayuda(ventana.acciones[clave]), f"{clave} quedó sin ayuda"


def test_el_selector_de_espacio_y_sus_items_explican_que_hacen(ventana):
    assert "Cambia de pestaña" in ventana.cinta.espacio.toolTip()
    for nombre, a in ventana.cinta.acciones_espacio.items():
        assert _ayuda(a), f"el espacio {nombre} quedó sin ayuda: {a.toolTip()!r}"


def test_el_menu_de_visualizacion_explica_cada_opcion(ventana):
    barra = ventana.barra_nav
    m = barra.menus["visualizacion"]
    acciones = [a for a in m.actions() if a.text()]
    estilos = next(a for a in acciones if a.text() == "Estilo visual").menu()
    assert all(_ayuda(a) for a in estilos.actions()), "algún estilo visual quedó sin ayuda"
    efectos = next(a for a in acciones if a.text() == "Efectos").menu()
    con_ayuda = [a for a in efectos.actions() if a.text() and a.isEnabled()
                 and "predefinido" not in a.text().lower()]
    assert all(_ayuda(a) for a in con_ayuda), "algún efecto quedó sin ayuda"
    camaras = next(a for a in acciones if a.text() == "Cámara").menu()
    assert all(_ayuda(a) for a in camaras.actions()), "alguna cámara quedó sin ayuda"
    rejilla = [a for a in barra.menus["rejilla"].actions() if a.text()]
    assert all(_ayuda(a) for a in rejilla[:3]), "la rejilla quedó sin ayuda"


def test_la_fila_de_grupos_de_la_cinta_tiene_aire(ventana):
    """El layout de la fila de grupos ya no va pegado: margen 0 en los cuatro lados era el hallazgo de
    espaciado de la auditoría (27 layouts en margen 0)."""
    fila = ventana.cinta.pila.currentWidget()
    lay = fila.layout()
    assert isinstance(lay, QHBoxLayout)
    m = lay.contentsMargins()
    assert (m.left(), m.top(), m.right(), m.bottom()) == (4, 3, 4, 3)
    assert lay.spacing() >= 8
