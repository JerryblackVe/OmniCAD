# -*- coding: utf-8 -*-
"""Fase 1 del plan del boceto: errores de la interfaz (B-94 rehacer, B-95 Suprimir y Repetir, B-97 voltear texto)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402

PLANO = g.Plano("XY")


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.show()
    yield v
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def boceto_abierto(ventana):
    mb = ventana.modo_boceto
    mb.iniciar(Boceto(), PLANO, {"op": None, "plano": "XY"})
    yield mb
    if mb.activo:
        mb.cancelar()


def _linea(lz, y):
    assert lz.aplicar_cambio(lambda: lz.b.agregar_linea((0, y), (10, y)))


def _tres_curvas(lz):
    for y in (0, 5, 10):
        _linea(lz, y)
    assert len(lz.b.curvas) == 3


# ---------------------------------------------------------------- B-94
def test_b94_rehacer_en_el_lienzo_vuelve_a_las_3_curvas(boceto_abierto):
    lz = boceto_abierto.lienzo
    _tres_curvas(lz)
    lz.deshacer()
    lz.deshacer()
    assert len(lz.b.curvas) == 1
    lz.rehacer()
    lz.rehacer()
    assert len(lz.b.curvas) == 3
    lz.rehacer()                                     # sin nada que rehacer: no hace nada
    assert len(lz.b.curvas) == 3


def test_b94_un_cambio_nuevo_vacia_la_pila_de_rehacer(boceto_abierto):
    lz = boceto_abierto.lienzo
    _tres_curvas(lz)
    lz.deshacer()
    _linea(lz, 20)
    lz.rehacer()
    assert len(lz.b.curvas) == 3 and not lz.pila_rehacer


def test_b94_ctrl_y_de_la_ventana_rehace_el_boceto_y_no_el_documento(ventana, boceto_abierto):
    lz, doc = boceto_abierto.lienzo, ventana.doc
    antes = doc.a_dict()
    _tres_curvas(lz)
    ventana._deshacer()
    ventana._deshacer()
    assert len(lz.b.curvas) == 1
    ventana._rehacer()
    ventana._rehacer()
    assert len(lz.b.curvas) == 3
    assert boceto_abierto.activo and doc.a_dict() == antes      # el documento no se tocó


# ---------------------------------------------------------------- B-95
def test_b95_suprimir_dentro_del_boceto_borra_la_seleccion_sin_salir(ventana, boceto_abierto):
    lz = boceto_abierto.lienzo
    _tres_curvas(lz)
    elegida = max(lz.b.curvas)
    lz.seleccion = [elegida]
    ventana._tecla_suprimir()
    assert boceto_abierto.activo and ventana.panel is None
    assert elegida not in lz.b.curvas and len(lz.b.curvas) == 2


def test_b95_suprimir_sin_seleccion_no_abre_el_dialogo_ni_sale(ventana, boceto_abierto):
    boceto_abierto.lienzo.seleccion = []
    ventana._tecla_suprimir()
    assert boceto_abierto.activo and ventana.panel is None


def test_b95_repetir_dentro_del_boceto_repite_la_ultima_herramienta_sin_salir(ventana, boceto_abierto):
    lz = boceto_abierto.lienzo
    boceto_abierto.herramienta("linea")
    boceto_abierto.herramienta("seleccionar")
    ventana.repetir_ultimo()
    assert boceto_abierto.activo and lz.herramienta == "linea" and ventana.panel is None
    repetir = ventana._items_radial()[0]                         # el ítem «Repetir» del menú radial
    assert repetir.texto.startswith("Repetir ") and repetir.activo


# ---------------------------------------------------------------- B-97
def test_b97_los_botones_de_volteo_del_panel_caracter_voltean_el_texto(ventana, boceto_abierto):
    mb = boceto_abierto
    tid = mb.lienzo.b.agregar_texto((0, 0), "HOLA", 10, 0, "Arial", False, False)
    mb.herramienta("texto")
    mb.caracter.b_voltear_h.setChecked(True)
    assert mb.lienzo.opciones["voltear_h"] is True
    mb.herramienta("seleccionar")
    mb.lienzo.editar_texto(tid, mb.lienzo.rect().center())       # editar parte de lo que el texto ya tiene
    assert not mb.caracter.b_voltear_h.isChecked()
    mb.caracter.b_voltear_v.setChecked(True)
    mb.caracter.b_voltear_h.setChecked(True)
    mb.lienzo.entrada.aceptado.emit(["HOLA", "10", "0", "0", "1"])
    t = mb.lienzo.b.curvas[tid]
    assert t.voltear_h and t.voltear_v
    mb.lienzo.editar_texto(tid, mb.lienzo.rect().center())
    mb.caracter.b_voltear_h.setChecked(False)
    mb.lienzo.entrada.aceptado.emit(["HOLA", "10", "0", "0", "1"])
    assert not t.voltear_h and t.voltear_v


def test_b97_edit_text_de_la_api_ya_voltea():
    s = api.Sesion()
    for nombre, args in (("create_sketch", {"name": "B"}), ("add_text", {"text": "HOLA", "height": 10})):
        assert api.llamar(s, nombre, args)["ok"]
    r = api.llamar(s, "edit_text", {"entity": 1, "flip_h": True, "flip_v": True})
    assert r["ok"], r
    texto = [e for e in api.llamar(s, "get_sketch", {})["result"]["entities"] if e["type"] == "text"][0]
    assert texto["flip_h"] is True and texto["flip_v"] is True
