# -*- coding: utf-8 -*-
"""Ubicación de la cota del boceto (línea de cota y texto movibles): modelo, API MCP/CLI y editor."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _sesion_con_linea():
    s = api.Sesion()
    llamar(s, "create_sketch", name="P")
    r = llamar(s, "draw_line", start_x=0, start_y=0, end_x=40, end_y=0)
    return s, r["entities"][0]["id"]


# ---------------------------------------------------------------- modelo
def test_ubicar_cota_guarda_desfase_y_texto_en_mm():
    b = Boceto()
    ln = b.agregar_rectangulo((0, 0), (40, 20))[0]
    k = b.cotas[b.agregar_cota("distancia", [ln], "40")]
    b.ubicar_cota(k, (25, -12))                                   # normal = izquierda de a→b (+Y): abajo es negativo
    assert k.datos["desfase"] == pytest.approx(-12) and k.datos["texto"] == pytest.approx(5)
    medida = b.medir_cota("distancia", [ln])
    assert medida == pytest.approx(40)                            # no cambia el valor ni la geometría


def test_cota_no_lineal_no_se_ubica():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 5)
    k = b.cotas[b.agregar_cota("radio", [c], "5")]
    b.ubicar_cota(k, (9, 9))
    assert b.ejes_cota(k) is None and "desfase" not in k.datos


def test_la_ubicacion_sobrevive_a_guardar_y_reabrir():
    b = Boceto()
    ln = b.agregar_rectangulo((0, 0), (40, 20))[0]
    k = b.cotas[b.agregar_cota("distancia", [ln], "40")]
    b.ubicar_cota(k, (25, -12))
    otro = Boceto.desde_dict(b.a_dict())
    assert otro.cotas[k.id].datos == k.datos


# ---------------------------------------------------------------- API
def test_add_dimension_con_offset_y_get_sketch():
    s, ln = _sesion_con_linea()
    d = llamar(s, "add_dimension", sketch="P", type="distance", entities=[ln], value=40, offset=7.5,
               text_offset=-3)
    assert d["dimension"]["offset"] == 7.5 and d["dimension"]["text_offset"] == -3
    k = llamar(s, "get_sketch")["dimensions"][0]
    assert k["offset"] == 7.5 and k["text_offset"] == -3 and k["value"] == 40


def test_edit_dimension_solo_ubicacion_no_cambia_el_valor_y_se_deshace():
    s, ln = _sesion_con_linea()
    d = llamar(s, "add_dimension", sketch="P", type="distance", entities=[ln], value=40)
    assert "offset" not in d["dimension"]
    e = llamar(s, "edit_dimension", dimension=d["dimension"]["id"], offset=-4)
    assert e["dimension"]["offset"] == -4 and e["dimension"]["expression"] == d["dimension"]["expression"] and e["dimension"]["value"] == 40
    llamar(s, "undo")
    assert "offset" not in llamar(s, "get_sketch")["dimensions"][0]


def test_la_ubicacion_sobrevive_a_recalcular_y_a_reabrir_el_documento():
    s, ln = _sesion_con_linea()
    llamar(s, "add_dimension", sketch="P", type="distance", entities=[ln], value=40, offset=9)
    llamar(s, "recompute_all")
    assert llamar(s, "get_sketch")["dimensions"][0]["offset"] == 9
    s2 = api.Sesion()
    s2.doc = Documento.desde_dict(s.doc.a_dict())
    assert llamar(s2, "get_sketch")["dimensions"][0]["offset"] == 9


def test_offset_invalido_o_en_cota_no_lineal_falla():
    s, ln = _sesion_con_linea()
    c = llamar(s, "draw_circle", center_x=0, center_y=20, radius=5)["entities"][0]["id"]
    r = api.llamar(s, "add_dimension", {"sketch": "P", "type": "radius", "entities": [c], "value": 5, "offset": 3})
    assert not r["ok"] and r["error_kind"] == "INVALID_DIMENSION"
    r = api.llamar(s, "add_dimension", {"sketch": "P", "type": "distance", "entities": [ln], "value": 40,
                                         "offset": float("nan")})
    assert not r["ok"]
    d = llamar(s, "add_dimension", sketch="P", type="distance", entities=[ln], value=40)
    r = api.llamar(s, "edit_dimension", {"dimension": d["dimension"]["id"]})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------- editor
@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _lienzo(app_qt, b):
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.ajustar_grilla = False
    lz.resize(800, 600)
    lz.show()
    return lz


def test_editor_arrastrar_la_cota_mueve_solo_su_ubicacion_y_deshace(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    b = Boceto()
    ln = b.agregar_rectangulo((0, 0), (20, 10))[0]
    cid = b.agregar_cota("distancia", [ln], "20")
    lz = _lienzo(app_qt, b)
    lz.grab()
    caja = lz._zonas_cotas[cid]
    lz.herramienta = "seleccionar"
    desde = caja.center().toPoint()
    QTest.mouseMove(lz, desde)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, desde)
    destino = lz.a_px(12, -9).toPoint()
    QTest.mouseMove(lz, lz.a_px(11, -8).toPoint())
    QTest.mouseMove(lz, destino)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, destino)
    k = lz.b.cotas[cid]
    assert k.datos["desfase"] == pytest.approx(-9, abs=0.3) and k.datos["texto"] == pytest.approx(2, abs=0.3)
    assert lz.b.medir_cota("distancia", [ln]) == pytest.approx(20) and lz.b.coords(lz.b.curvas[ln].p2) == (20, 0)
    lz.deshacer()
    assert "desfase" not in lz.b.cotas[cid].datos
    lz.close()
    lz.deleteLater()


def test_editor_cota_nueva_muestra_las_lineas_y_guarda_donde_se_clico(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    b = Boceto()
    ln = b.agregar_rectangulo((0, 0), (20, 10))[0]
    lz = _lienzo(app_qt, b)
    lz.herramienta = "cota"
    ent_px = lz.a_px(10, 0).toPoint()
    QTest.mouseMove(lz, ent_px)
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, ent_px)
    assert lz.picks == [ln]
    lz._pos_cursor = lz.a_px(10, -6)                              # línea elegida: la cota sigue al cursor
    viva = lz._cota_viva()
    assert viva is not None and viva.datos["desfase"] == pytest.approx(-6, abs=0.3)
    lz.grab()
    clic = lz.a_px(10, -6).toPoint()
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, clic)
    assert lz.entrada is not None and lz._cota_previa is not None   # caja del valor + líneas provisionales
    lz.grab()
    lz.entrada.campos[0].setText("20")
    lz.entrada.aceptado.emit(["20"])
    (k,) = lz.b.cotas.values()
    assert k.datos["desfase"] == pytest.approx(-6, abs=0.3) and math.isfinite(k.datos["texto"])
    assert lz._cota_previa is None
    lz.close()
    lz.deleteLater()
