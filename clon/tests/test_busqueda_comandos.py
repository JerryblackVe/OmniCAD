# -*- coding: utf-8 -*-
"""Búsqueda de comandos de la caja de herramientas (ui/busqueda_comandos.py)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.ui.busqueda_comandos import coincidencias, comandos_disponibles, nombre_accion  # noqa: E402

ENTRADAS = [("empalme_3d", "Empalme"), ("chaflan_3d", "Chaflán"), ("patron_circular_3d", "Patrón circular"),
            ("patron_rectangular_3d", "Patrón rectangular"), ("extruir", "Extruir"), ("sup_extruir", "Extruir"),
            ("mover_copiar", "Mover/copiar"), ("plano_desfase", "Plano de desfase"), ("desfase_cara", "Cara de desfase")]


def test_sin_tildes_ni_mayusculas():
    assert coincidencias("CHAFLAN", ENTRADAS) == ["chaflan_3d"]
    assert coincidencias("chaflán", ENTRADAS) == ["chaflan_3d"]


def test_todas_las_palabras_en_cualquier_orden():
    assert coincidencias("circ patron", ENTRADAS) == ["patron_circular_3d"]
    assert coincidencias("patron", ENTRADAS) == ["patron_circular_3d", "patron_rectangular_3d"]


def test_primero_lo_que_empieza_igual_despues_palabra_despues_el_resto():
    # ninguno empieza con «desfase»: los dos lo tienen como palabra y va primero el nombre más corto
    assert coincidencias("desfase", ENTRADAS) == ["desfase_cara", "plano_desfase"]
    assert coincidencias("copiar", ENTRADAS) == ["mover_copiar"]        # palabra después de «/»
    assert coincidencias("fla", ENTRADAS) == ["chaflan_3d"]             # en el medio de una palabra


def test_vacio_o_sin_resultados_y_tope():
    assert coincidencias("   ", ENTRADAS) == []
    assert coincidencias("zzz", ENTRADAS) == []
    assert len(coincidencias("e", ENTRADAS, maximo=3)) == 3


def test_disponibles_sin_grisados_ni_filtros_ni_la_caja_ni_repetidos():
    QApplication.instance() or QApplication([])
    acciones = {}
    for clave, texto, activa in (("extruir", "Extruir	E", True), ("revolucion", "Revolución", False),
                                 ("filtro_caras", "Caras", True), ("caja_herramientas", "Caja de herramientas	S", True),
                                 ("sup_extruir", "Extruir", True), ("chaflan_3d", "&Chaflán", True)):
        a = QAction(texto)
        a.setEnabled(activa)
        acciones[clave] = a
    assert comandos_disponibles(acciones) == [("extruir", "Extruir"), ("chaflan_3d", "Chaflán")]
    assert nombre_accion(acciones["caja_herramientas"]) == "Caja de herramientas"
