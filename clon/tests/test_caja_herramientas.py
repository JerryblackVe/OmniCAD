# -*- coding: utf-8 -*-
"""Caja de herramientas de la tecla S (ui/caja_herramientas.py), como la «Model Toolbox» de Fusion."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from omnicad.ui.caja_herramientas import CajaHerramientas, leer_fijados  # noqa: E402
from omnicad.ui.preferencias import Preferencias  # noqa: E402

COMANDOS = [("extruir", "Extruir\tE", True), ("empalme_3d", "Empalme\tF", True), ("chaflan_3d", "Chaflán", True),
            ("revolucion", "Revolución", False), ("sk_linea", "Línea\tL", True)]


@pytest.fixture
def caja(tmp_path):
    QApplication.instance() or QApplication([])
    ventana = QWidget()
    ventana.resize(900, 700)
    disparadas = []
    acciones = {}
    for clave, texto, activa in COMANDOS:
        a = QAction(texto, ventana)
        a.setEnabled(activa)
        a.triggered.connect(lambda _=False, c=clave: disparadas.append(c))
        acciones[clave] = a
    prefs = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    c = CajaHerramientas(acciones, prefs, ventana)
    ventana.show()
    QTest.qWaitForWindowExposed(ventana)
    c.abrir("diseno", QPoint(100, 100))
    yield c, prefs, disparadas
    c.cerrar()
    ventana.close()
    ventana.deleteLater()


def _atajos(c):
    return [c.atajos.item(i).data(Qt.UserRole) for i in range(c.atajos.count())]


def _resultados(c):
    return [c.resultados.item(i).data(Qt.UserRole) for i in range(c.resultados.count())]


def test_de_fabrica_extruir_y_empalme_en_diseno_y_nada_en_boceto(caja):
    c, prefs, _ = caja
    assert c.isVisible() and c.titulo.text() == "ATAJOS DE DISEÑO" and QApplication.focusWidget() is c.campo
    assert _atajos(c) == ["extruir", "empalme_3d"]
    c.abrir("boceto", QPoint(10, 10))
    assert c.titulo.text() == "ATAJOS DE BOCETO" and _atajos(c) == [] and c.vacio.isVisible()


def test_buscar_lista_solo_lo_disponible_y_enter_ejecuta(caja):
    c, _, disparadas = caja
    QTest.keyClicks(c.campo, "r")
    assert "revolucion" not in _resultados(c)              # grisado: no aparece
    c.campo.clear()
    QTest.keyClicks(c.campo, "chaf")
    assert c.resultados.isVisible() and _resultados(c) == ["chaflan_3d"]
    QTest.keyClick(c.campo, Qt.Key_Return)
    QTest.qWait(10)
    assert disparadas == ["chaflan_3d"] and not c.isVisible()


def test_flechas_recorren_los_resultados(caja):
    c, _, disparadas = caja
    QTest.keyClicks(c.campo, "e")                          # Extruir, Empalme, Línea…
    primero = c.resultados.currentItem().data(Qt.UserRole)
    QTest.keyClick(c.campo, Qt.Key_Down)
    segundo = c.resultados.currentItem().data(Qt.UserRole)
    assert segundo != primero
    QTest.keyClick(c.campo, Qt.Key_Return)
    QTest.qWait(10)
    assert disparadas == [segundo]


def test_la_chinche_fija_y_quita_y_se_guarda(caja):
    c, prefs, _ = caja
    QTest.keyClicks(c.campo, "chaf")
    fila = c.resultados.itemWidget(c.resultados.item(0))
    assert not fila.chinche.isChecked()
    fila.chinche.click()
    assert leer_fijados(prefs, "diseno") == ["extruir", "empalme_3d", "chaflan_3d"]
    fila.chinche.click()
    assert leer_fijados(prefs, "diseno") == ["extruir", "empalme_3d"]
    c.campo.clear()
    QTest.keyClicks(c.campo, "empal")
    assert c.resultados.itemWidget(c.resultados.item(0)).chinche.isChecked()     # Empalme ya viene fijado


def test_reordenar_guarda_el_orden_y_conserva_los_que_no_existen(caja):
    c, prefs, _ = caja
    prefs["atajos/diseno"] = "extruir,comando_viejo,empalme_3d"
    c.abrir("diseno", QPoint(0, 0))
    assert _atajos(c) == ["extruir", "empalme_3d"]         # el que no existe no se muestra…
    c.atajos.insertItem(0, c.atajos.takeItem(1))           # lo que hace arrastrar Empalme adelante
    c.atajos.reordenada.emit()
    assert leer_fijados(prefs, "diseno") == ["empalme_3d", "extruir", "comando_viejo"]   # …pero no se pierde


def test_clic_en_un_atajo_ejecuta(caja):
    c, _, disparadas = caja
    c.atajos.itemClicked.emit(c.atajos.item(0))
    QTest.qWait(10)
    assert disparadas == ["extruir"] and not c.isVisible()


def test_esc_y_clic_afuera_cierran_sin_ejecutar(caja):
    c, _, disparadas = caja
    QTest.keyClick(c.campo, Qt.Key_Escape)
    assert not c.isVisible()
    c.abrir("diseno", QPoint(100, 100))
    QTest.mouseClick(c.parentWidget(), Qt.LeftButton, pos=QPoint(850, 650))
    assert not c.isVisible() and disparadas == []


def test_no_se_sale_de_la_ventana(caja):
    c, _, _ = caja
    c.abrir("diseno", QPoint(5000, 5000))
    padre = c.parentWidget().rect()
    assert padre.contains(c.geometry())


def test_al_cerrar_el_foco_vuelve_adonde_estaba(caja):
    # Si no vuelve, en un boceto la tecla «2» dispara «Selección de forma libre» en vez de la entrada de longitud.
    from PySide6.QtWidgets import QLineEdit
    c, _, _ = caja
    c.cerrar()
    lienzo = QLineEdit(c.parentWidget())
    lienzo.show()
    lienzo.setFocus()
    QTest.qWait(10)
    c.abrir("boceto", QPoint(50, 50))
    assert QApplication.focusWidget() is c.campo
    QTest.keyClick(c.campo, Qt.Key_Escape)
    assert QApplication.focusWidget() is lienzo
