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


def test_editor_cota_se_agarra_de_su_linea_y_solo_mueve_la_linea(app_qt):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    b = Boceto()
    ln = b.agregar_rectangulo((0, 0), (60, 10))[0]
    cid = b.agregar_cota("distancia", [ln], "60")
    b.cotas[cid].datos.update(desfase=-6.0, texto=0.0)
    lz = _lienzo(app_qt, b)
    lz.herramienta = "seleccionar"
    lz.grab()
    a, z = lz._trazos_cotas[cid][0]                            # la línea de cota (las flechas no cuentan)
    desde = (a + (z - a) * 0.1).toPoint()                     # lejos del texto, que está en el centro
    assert not lz._zonas_cotas[cid].adjusted(-4, -4, 4, 4).contains(QPointF(desde))
    assert lz._zona_en(QPointF(desde)) == cid
    assert lz._zona_en(QPointF(desde.x(), desde.y() + 20)) is None
    QTest.mouseMove(lz, desde)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, desde)
    destino = lz.a_px(4, -11).toPoint()
    QTest.mouseMove(lz, lz.a_px(4, -8).toPoint())
    QTest.mouseMove(lz, destino)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, destino)
    k = lz.b.cotas[cid]
    assert k.datos["desfase"] == pytest.approx(-11, abs=0.3) and k.datos["texto"] == 0.0    # el texto no se corrió
    assert lz.b.medir_cota("distancia", [ln]) == pytest.approx(60)
    lz.deshacer()
    assert lz.b.cotas[cid].datos["desfase"] == -6.0
    lz.close()
    lz.deleteLater()


def test_arrastrar_una_cota_de_angulo_al_otro_lado_cambia_el_cuadrante_que_mide():
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (20, 0))
    l2 = b.agregar_linea((0, 0), (10, 10))
    k = b.cotas[b.agregar_cota("angulo", [l1, l2], "45")]
    b.mover_cota(k, (8, 3))                               # entre las dos semirrectas: el ángulo de 45°
    assert k.datos["cuadrante"] == 0 and b.medir(k) == pytest.approx(45)
    b.mover_cota(k, (-8, 3))                              # del otro lado del vértice: el suplementario
    assert k.datos["cuadrante"] == 1 and b.medir(k) == pytest.approx(135)
    assert k.datos["ubic"] == [-8, 3] and k.expresion == "45"        # la expresión queda
    b.mover_cota(k, (8, 3))
    assert b.medir(k) == pytest.approx(45)


def test_editor_arrastrar_la_cota_de_angulo_al_lado_derecho_la_cambia_de_cuadrante(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (40, 0))
    l2 = b.agregar_linea((0, 0), (0, 40))
    cid = b.agregar_cota("angulo", [l1, l2], "90", {"cuadrante": 2})      # el del lado izquierdo/abajo del vértice
    lz = _lienzo(app_qt, b)
    lz.herramienta = "seleccionar"
    lz.grab()
    desde = lz._zonas_cotas[cid].center().toPoint()
    QTest.mouseMove(lz, desde)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, desde)
    destino = lz.a_px(15, 15).toPoint()                                   # arriba y a la derecha del vértice
    QTest.mouseMove(lz, lz.a_px(-5, -5).toPoint())
    QTest.mouseMove(lz, destino)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, destino)
    assert lz.b.cotas[cid].datos["cuadrante"] == 0
    assert lz.b.medir(lz.b.cotas[cid]) == pytest.approx(90)
    lz.deshacer()
    assert lz.b.cotas[cid].datos["cuadrante"] == 2
    lz.close()
    lz.deleteLater()


def test_editor_la_zona_de_una_cota_vertical_es_alta_como_su_texto_girado(app_qt):
    b = Boceto()
    vertical = b.agregar_linea((0, 0), (0, 60))
    horizontal = b.agregar_linea((10, 0), (70, 0))
    cv, ch = b.agregar_cota("distancia", [vertical], "60"), b.agregar_cota("distancia", [horizontal], "60")
    lz = _lienzo(app_qt, b)
    lz.grab()
    alta, ancha = lz._zonas_cotas[cv], lz._zonas_cotas[ch]
    assert alta.height() > alta.width() and ancha.width() > ancha.height()       # el recuadro de agarre abraza el texto
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


def test_editor_el_texto_de_la_cota_tiene_fondo_del_lienzo_y_girado(app_qt):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor
    b = Boceto()
    horizontal = b.agregar_linea((0, 40), (60, 40))
    vertical = b.agregar_linea((0, 0), (0, 60))
    ch = b.agregar_cota("distancia", [horizontal], "60")
    cv = b.agregar_cota("distancia", [vertical], "60")
    lz = _lienzo(app_qt, b)
    lz.grab()
    fondo_h, fondo_v = lz._fondos_cotas[ch], lz._fondos_cotas[cv]
    zona_h, zona_v = lz._zonas_cotas[ch], lz._zonas_cotas[cv]
    assert fondo_h.contains(zona_h) and fondo_v.contains(zona_v)
    assert fondo_h.width() > fondo_h.height()              # el fondo sigue al texto horizontal
    assert fondo_v.width() < fondo_v.height()              # y gira con el vertical
    assert lz._color_fondo() == QColor(250, 250, 252)
    # el fondo tapa una línea que pasa por detrás del texto: sin él se vería el color de la línea
    u, v = lz.a_mm(fondo_h.center())
    b.agregar_linea((u - 40, v), (u + 40, v))
    lz.resolver()
    img = lz.grab().toImage()
    punto = QPointF(fondo_h.left() + 1, fondo_h.center().y()).toPoint()
    assert img.pixelColor(punto) == lz._color_fondo()
    lz.close()
    lz.deleteLater()


def test_editor_las_lineas_auxiliares_dejan_hueco_y_sobresalen(app_qt):
    b = Boceto()
    ln = b.agregar_linea((0, 0), (40, 0))
    cid = b.agregar_cota("distancia", [ln], "40")
    b.cotas[cid].datos.update(desfase=-6.0, texto=0.0)
    lz = _lienzo(app_qt, b)
    lz.grab()
    trazos = lz._trazos_cotas[cid]
    assert len(trazos) == 3                               # línea de cota + dos auxiliares
    dim = trazos[0]
    for aux in trazos[1:]:
        pa = min((lz.a_px(0, 0), lz.a_px(40, 0)),
                 key=lambda q: math.dist((aux[0].x(), aux[0].y()), (q.x(), q.y())))
        qa = min(dim, key=lambda q: math.dist((aux[1].x(), aux[1].y()), (q.x(), q.y())))
        assert math.dist((aux[0].x(), aux[0].y()), (pa.x(), pa.y())) == pytest.approx(3)
        assert math.dist((aux[1].x(), aux[1].y()), (qa.x(), qa.y())) == pytest.approx(4)
    assert b.medir_cota("distancia", [ln]) == pytest.approx(40)
    lz.close()
    lz.deleteLater()


def test_editor_la_linea_auxiliar_agarra_la_cota_y_la_curva_gana(app_qt):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    b = Boceto()
    ln = b.agregar_linea((0, 0), (60, 0))
    cid = b.agregar_cota("distancia", [ln], "60")
    b.cotas[cid].datos.update(desfase=-6.0, texto=0.0)
    lz = _lienzo(app_qt, b)
    lz.herramienta = "seleccionar"
    lz.grab()
    aux = lz._trazos_cotas[cid][1]
    desde = ((aux[0] + aux[1]) / 2).toPoint()
    assert lz._zona_en(QPointF(desde)) == cid
    QTest.mouseMove(lz, desde)
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, desde)
    destino = lz.a_px(4, -11).toPoint()
    QTest.mouseMove(lz, lz.a_px(4, -8).toPoint())
    QTest.mouseMove(lz, destino)
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, destino)
    k = lz.b.cotas[cid]
    assert k.datos["desfase"] == pytest.approx(-11, abs=0.3) and k.datos["texto"] == 0.0
    assert b.medir_cota("distancia", [ln]) == pytest.approx(60)
    lz.deshacer()
    assert lz.b.cotas[cid].datos["desfase"] == -6.0
    # un punto del boceto sobre la auxiliar gana: la cota no se agarra ahí
    pid = b.agregar_punto(0, -6)
    lz.grab()
    punto = lz.a_px(0, -6).toPoint()
    assert lz.entidad_en(QPointF(punto)) == pid
    assert lz._zona_en(QPointF(punto)) is None
    lz.close()
    lz.deleteLater()


def test_editor_menu_de_la_cota_edita_el_valor_y_renombra(app_qt, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    b = Boceto()
    ln = b.agregar_linea((0, 0), (20, 0))
    otro = b.agregar_linea((0, 10), (20, 10))
    cid = b.agregar_cota("distancia", [ln], "20")
    segundo = b.agregar_cota("distancia", [otro], "20")
    lz = _lienzo(app_qt, b)
    menu = lz._menu_cota(cid)
    textos = [a.text() for a in menu.actions() if a.text()]
    assert "Editar valor…" in textos and "Renombrar parámetro…" in textos
    next(a for a in menu.actions() if a.text() == "Editar valor…").trigger()
    assert lz.entrada is not None and lz._cota_editada == cid
    lz.entrada.campos[0].setText("25")
    lz.entrada.aceptado.emit(["25"])
    assert lz.b.cotas[cid].expresion == "25"
    lz.deshacer()
    assert lz.b.cotas[cid].expresion == "20"
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("ANCHO", True)))
    lz.renombrar_cota(cid)
    assert lz.b.cotas[cid].nombre == "ANCHO"
    lz.deshacer()
    assert not lz.b.cotas[cid].nombre
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("1malo", True)))
    lz.renombrar_cota(cid)
    assert not lz.b.cotas[cid].nombre and "inválido" in mensajes[-1]
    lz.b.cotas[segundo].nombre = "ANCHO"
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("ANCHO", True)))
    lz.renombrar_cota(cid)
    assert not lz.b.cotas[cid].nombre and "Ya existe" in mensajes[-1]
    lz.close()
    lz.deleteLater()


def test_editor_al_pasar_el_mouse_la_cota_muestra_nombre_y_valor(app_qt, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QToolTip
    b = Boceto()
    ln = b.agregar_linea((0, 0), (20, 0))
    cid = b.agregar_cota("distancia", [ln], "20")
    b.cotas[cid].nombre = "ANCHO"
    lz = _lienzo(app_qt, b)
    lz.herramienta = "seleccionar"
    lz.grab()
    textos = []
    monkeypatch.setattr(QToolTip, "showText", staticmethod(lambda pos, texto, *a, **k: textos.append(texto)))
    QTest.mouseMove(lz, lz._zonas_cotas[cid].center().toPoint())
    assert lz._cita_sobre == cid and textos[-1] == "ANCHO : 20 mm"
    QTest.mouseMove(lz, QPoint(750, 550))
    assert lz._cita_sobre is None
    lz.b.cotas[cid].nombre = ""
    lz.grab()
    QTest.mouseMove(lz, lz._zonas_cotas[cid].center().toPoint())
    assert textos[-1].startswith("d1 : 20 mm")
    lz.herramienta = "linea"
    QTest.mouseMove(lz, QPoint(750, 550))
    assert lz._cita_sobre is None
    lz.close()
    lz.deleteLater()
