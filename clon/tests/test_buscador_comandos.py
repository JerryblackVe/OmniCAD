# -*- coding: utf-8 -*-
"""Buscador de comandos de la cinta (ui/buscador_comandos.py): la búsqueda pura y el campo con acciones reales."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402

from omnicad.ui.buscador_comandos import BuscadorComandos, coincidencias  # noqa: E402

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


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def buscador(app_qt):
    ventana = QWidget()
    ventana.resize(800, 500)
    disparadas = []
    acciones = {}
    for clave, texto, activa in (("extruir", "Extruir\tE", True), ("chaflan_3d", "Chaflán", True),
                                 ("revolucion", "Revolución", False), ("filtro_caras", "Caras", True),
                                 ("buscar_comando", "Buscar comando\tControl+K", True)):
        a = QAction(texto, ventana)
        a.setEnabled(activa)
        a.triggered.connect(lambda _=False, c=clave: disparadas.append(c))
        acciones[clave] = a
    campo = BuscadorComandos(acciones)
    QVBoxLayout(ventana).addWidget(campo, 0, Qt.AlignTop | Qt.AlignRight)
    ventana.show()
    QTest.qWaitForWindowExposed(ventana)
    campo.enfocar()
    yield campo, disparadas
    ventana.close()
    ventana.deleteLater()


def test_solo_comandos_disponibles(buscador):
    campo, _ = buscador
    claves = [c for c, _n in campo.disponibles()]
    # sin grisados (Revolución), sin filtros de selección ni el propio buscador
    assert claves == ["extruir", "chaflan_3d"]


def test_escribir_lista_y_enter_ejecuta_el_primero(buscador):
    campo, disparadas = buscador
    QTest.keyClicks(campo, "chafla")
    assert campo.lista.isVisible()
    assert [campo.lista.item(i).text() for i in range(campo.lista.count())] == ["Chaflán"]
    QTest.keyClick(campo, Qt.Key_Return)
    QTest.qWait(10)
    assert disparadas == ["chaflan_3d"]
    assert campo.text() == "" and not campo.lista.isVisible()


def test_el_atajo_se_muestra_y_sin_coincidencias_avisa_sin_ejecutar(buscador):
    campo, disparadas = buscador
    QTest.keyClicks(campo, "extr")
    assert campo.lista.item(0).text() == "Extruir    E"
    campo.clear()
    QTest.keyClicks(campo, "qwerty")
    assert campo.lista.count() == 1 and "Ningún comando" in campo.lista.item(0).text()
    QTest.keyClick(campo, Qt.Key_Return)
    QTest.qWait(10)
    assert disparadas == []


def test_escape_cierra_y_limpia(buscador):
    campo, disparadas = buscador
    QTest.keyClicks(campo, "e")
    QTest.keyClick(campo, Qt.Key_Escape)
    assert campo.text() == "" and not campo.lista.isVisible() and disparadas == []
