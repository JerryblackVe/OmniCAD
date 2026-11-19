# -*- coding: utf-8 -*-
"""PREP: comandos de boceto y de SELECCIONAR sin test automático (tabla de docs/plan_boceto_perfecto.md ›
Cobertura): las restricciones Colineal, Concéntrica, Igual y Perpendicular, Terminar con AutoConstrain, y
Seleccionar todo / Invertir selección / Por nombre / Por tamaño / En ventana / De forma libre."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto, grados_de_libertad, resolver
from omnicad.timeline.documento import Documento
from omnicad.timeline.parametros import TablaParametros

PLANO = g.Plano("XY")


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _lienzo(app_qt):
    from omnicad.ui.editor_boceto import Lienzo
    lz = Lienzo(Boceto(), TablaParametros().evaluar, plano=PLANO)
    lz.ajustar_grilla = False
    return lz


def _clic(lz, herramienta, *puntos):
    """Elegir la herramienta de restricción y hacer clic sobre cada curva (en mm), como una persona."""
    lz.set_herramienta(herramienta)
    for x, y in puntos:
        lz._clic_restriccion(lz.a_px(x, y))


def _valores(b):
    return {k.id: float(k.expresion) for k in b.cotas.values()}


# ---------------------------------------------------------------- RESTRICCIONES
def test_sk_r_colineal_deja_las_dos_lineas_en_la_misma_recta(app_qt):
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (10, 0))
    l2 = lz.b.agregar_linea((0, 5), (10, 5))
    _clic(lz, "r_colineal", (5, 0), (5, 5))
    assert any(r.tipo == "colineal" for r in lz.b.restricciones.values())
    assert resolver(lz.b).ok
    (a, b), (c, d) = lz.b._extremos_linea(l1), lz.b._extremos_linea(l2)
    ux, uy = b[0] - a[0], b[1] - a[1]
    for p in (c, d):                       # los extremos de la segunda línea caen sobre la recta de la primera
        assert abs((p[0] - a[0]) * uy - (p[1] - a[1]) * ux) / math.hypot(ux, uy) == pytest.approx(0, abs=1e-6)


def test_sk_r_concentrica_comparte_el_centro_y_conserva_los_radios(app_qt):
    lz = _lienzo(app_qt)
    c1 = lz.b.agregar_circulo((0, 0), 5)
    c2 = lz.b.agregar_circulo((20, 0), 3)
    _clic(lz, "r_concentrica", (5, 0), (23, 0))
    assert resolver(lz.b).ok
    assert lz.b.coords(lz.b.curvas[c2].centro) == pytest.approx(lz.b.coords(lz.b.curvas[c1].centro), abs=1e-6)
    assert lz.b.radio(c1) == pytest.approx(5) and lz.b.radio(c2) == pytest.approx(3)


def test_sk_r_igual_iguala_los_largos(app_qt):
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (10, 0))
    l2 = lz.b.agregar_linea((0, 10), (20, 10))
    _clic(lz, "r_igual", (5, 0), (10, 10))
    assert resolver(lz.b).ok
    largos = [math.dist(*lz.b._extremos_linea(k)) for k in (l1, l2)]
    assert largos[0] == pytest.approx(largos[1], abs=1e-6)


def test_sk_r_perpendicular_forma_90_grados(app_qt):
    lz = _lienzo(app_qt)
    l1 = lz.b.agregar_linea((0, 0), (10, 0))
    l2 = lz.b.agregar_linea((0, 20), (10, 30))           # a 45° de la primera
    _clic(lz, "r_perpendicular", (5, 0), (5, 25))
    assert resolver(lz.b).ok
    d1, d2 = lz.b._direccion(l1), lz.b._direccion(l2)
    assert d1[0] * d2[0] + d1[1] * d2[1] == pytest.approx(0, abs=1e-6)


# ---------------------------------------------------------------- TERMINAR
@pytest.fixture
def ventana(app_qt, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    QTest.qWait(1)
    v.set_documento(Documento())
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app_qt.processEvents()


def test_sk_terminar_auto_restringe_el_boceto_y_termina(ventana):
    from PySide6.QtTest import QTest
    b = Boceto()
    b.agregar_rectangulo((0, 0), (40, 25))
    b.agregar_circulo((20, 12), 5)
    ventana.modo_boceto.iniciar(b, PLANO, {"op": None, "plano": "XY"})
    QTest.qWait(1)
    boceto = ventana.modo_boceto.boceto
    termino, agregado = ventana.modo_boceto.terminar_con_autorestringir()
    assert termino and not ventana.modo_boceto.activo and agregado
    assert grados_de_libertad(boceto, _valores(boceto)) == 0
    assert resolver(boceto, _valores(boceto)).ok


# ---------------------------------------------------------------- SELECCIONAR
@pytest.fixture
def con_cuerpos(ventana):
    from PySide6.QtTest import QTest
    from omnicad import api
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    assert api.llamar(s, "create_cylinder", {"height": 30, "radius": 10, "x": 90})["ok"]
    ventana.set_documento(s.doc)
    s.doc.modificado = False
    QTest.qWait(20)
    ventana.visor.encuadrar()
    QTest.qWait(10)
    return ventana


def _ids(v):
    return sorted(h["ref"]["cuerpo"] for h in v.seleccion if h["ref"].get("cuerpo"))


def _arrastre(visor, desde, hasta):
    """Arrastre con el botón izquierdo como una persona: apretar, varios movimientos, soltar."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    def ev(tipo, p, boton, botones):
        p = QPointF(*p)
        QApplication.sendEvent(visor, QMouseEvent(tipo, p, visor.mapToGlobal(p), boton, botones, Qt.NoModifier))
    ev(QEvent.MouseButtonPress, desde, Qt.LeftButton, Qt.LeftButton)
    for k in range(1, 6):
        ev(QEvent.MouseMove, [a + (b - a) * k / 5 for a, b in zip(desde, hasta, strict=True)],
           Qt.NoButton, Qt.LeftButton)
    ev(QEvent.MouseButtonRelease, hasta, Qt.LeftButton, Qt.NoButton)


def test_seleccionar_todo_elige_los_cuerpos_visibles(con_cuerpos):
    v = con_cuerpos
    v.acciones["seleccionar_todo"].trigger()
    assert _ids(v) == sorted(v.doc.estado_final.cuerpos)


def test_invertir_seleccion_elige_los_no_elegidos(con_cuerpos):
    v = con_cuerpos
    ids = sorted(v.doc.estado_final.cuerpos)
    v.seleccionar_cuerpos([ids[0]])
    v.acciones["invertir_seleccion"].trigger()
    assert _ids(v) == [ids[1]]


def test_seleccion_nombre_elige_por_su_nombre(con_cuerpos, monkeypatch):
    import omnicad.ui.ventana as mod
    v = con_cuerpos
    estado = v.doc.estado_final
    nombres = {v.nombre_cuerpo(c): c.id for c in estado.cuerpos.values()}
    nombre, cid = next(iter(nombres.items()))

    class Dialogo:
        @staticmethod
        def getText(*_a, **_k):
            return nombre, True
    monkeypatch.setattr(mod, "QInputDialog", Dialogo)
    v.acciones["seleccion_nombre"].trigger()
    assert _ids(v) == [cid]


def test_seleccion_tamano_filtra_por_la_diagonal(con_cuerpos, monkeypatch):
    import omnicad.ui.ventana as mod
    v = con_cuerpos
    diagonales = {}
    for m in v.visor._mallas:
        diag = float(((m["v"].max(axis=0) - m["v"].min(axis=0)) ** 2).sum() ** 0.5)
        diagonales[m["id"]] = diag
    grande = max(diagonales, key=diagonales.get)
    respuestas = iter([(100.0, True), (200.0, True)])       # mínimo y máximo de la diagonal

    class Dialogo:
        @staticmethod
        def getDouble(*_a, **_k):
            return next(respuestas)
    monkeypatch.setattr(mod, "QInputDialog", Dialogo)
    v.acciones["seleccion_tamano"].trigger()
    assert _ids(v) == [grande] and diagonales[grande] > 100 > min(diagonales.values())


def test_sel_ventana_elige_lo_que_encierra_y_vuelve_al_modo_comun(con_cuerpos):
    v = con_cuerpos
    v.acciones["sel_ventana"].trigger()
    assert v.visor.modo == "sel_ventana"
    _arrastre(v.visor, (3, 3), (v.visor.width() - 3, v.visor.height() - 3))
    assert _ids(v) == sorted(v.doc.estado_final.cuerpos)
    v.acciones["sel_ventana"].trigger()
    assert v.visor.modo is None


def test_sel_libre_elige_lo_que_encierra_el_lazo(con_cuerpos):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    v = con_cuerpos
    v.acciones["sel_libre"].trigger()
    assert v.visor.modo == "sel_libre"

    def ev(tipo, p, boton, botones):
        p = QPointF(*p)
        QApplication.sendEvent(v.visor, QMouseEvent(tipo, p, v.visor.mapToGlobal(p), boton, botones, Qt.NoModifier))
    an, al = v.visor.width() - 3, v.visor.height() - 3
    ev(QEvent.MouseButtonPress, (3, 3), Qt.LeftButton, Qt.LeftButton)
    for p in ((an, 3), (an, al), (3, al)):                 # un lazo alrededor de toda la vista
        ev(QEvent.MouseMove, p, Qt.NoButton, Qt.LeftButton)
    ev(QEvent.MouseButtonRelease, (3, al), Qt.LeftButton, Qt.NoButton)
    assert _ids(v) == sorted(v.doc.estado_final.cuerpos)
    v.acciones["sel_libre"].trigger()
    assert v.visor.modo is None
