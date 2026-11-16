# -*- coding: utf-8 -*-
"""FL-3b: Aceptar, deshacer y rehacer con el cálculo en el proceso aparte no esperan en la ventana: el cálculo corre en
otro hilo con una barra y Cancelar (o Esc) abajo, que deja el documento como estaba; mientras, la cámara se mueve (P-173)."""
import time

import pytest
import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QProgressDialog

from omnicad import api
from omnicad.nucleo import aislado
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui import visor3d
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def ventana(tmp_path, monkeypatch):
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 1)      # un documento chico también calcula aparte
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    for i in range(3):
        assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": i * 14})["ok"]
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    v.activateWindow()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()
    aislado.cerrar_trabajador()


def _esperar(condicion, segundos=60):
    limite = time.monotonic() + segundos
    while not condicion() and time.monotonic() < limite:
        QTest.qWait(20)
    assert condicion()


def _panel_mover(v):
    """Mover/copiar el primer cuerpo 5 mm en Z, con la previa ya calculada."""
    panel = v.ejecutar_comando(CATALOGO["mover_copiar"]())
    campo = next(c for c in panel.campos if c.clave == "cuerpos")
    panel._activar(campo)
    panel._elegida(hit_desde_ref({"tipo": "cuerpo", "cuerpo": next(iter(v.doc.estado_final.cuerpos))}, v.doc.estado_final))
    dz = panel.widgets["dz"]
    dz = dz if isinstance(dz, QLineEdit) else next(c for c in dz.findChildren(QLineEdit) if c.isVisible())
    QTest.mouseClick(dz, Qt.LeftButton)
    QTest.keyClick(dz, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(dz, "5")
    QTest.keyClick(dz, Qt.Key_Tab)
    _esperar(lambda: not panel._t_previa.isActive() and panel._hijo_previa is None and panel._previa_ok)
    return panel


def _vuelve_enseguida(accion):
    inicio = time.perf_counter()
    accion()
    return time.perf_counter() - inicio


def test_fl3b_aceptar_deshacer_y_rehacer_vuelven_enseguida(monkeypatch, ventana):
    v = ventana
    tareas, correr_json = [], aislado.correr_json
    monkeypatch.setattr(aislado, "correr_json", lambda tarea, *a, **k: tareas.append(tarea) or correr_json(tarea, *a, **k))
    pasos = len(v.doc.operaciones)
    panel = _panel_mover(v)
    tareas.clear()
    teselados, teselar = [], visor3d.teselar_cuerpo
    monkeypatch.setattr(visor3d, "teselar_cuerpo", lambda *a, **k: teselados.append(1) or teselar(*a, **k))
    assert _vuelve_enseguida(lambda: QTest.mouseClick(panel.boton_ok, Qt.LeftButton)) < 0.25
    _esperar(lambda: len(v.doc.operaciones) == pasos + 1 and v.panel is None)
    assert not teselados                    # el cuerpo movido reusa la malla de la previa: no se vuelve a mallar
    assert aislado._trabajador is not None  # cerrar la barra no es Cancelar: el trabajador vivo sigue (deshacer, 59 s → 2 s)
    assert tareas.count("prevuelo_cambio") <= 1           # el paso se calcula una vez (o reusa la previa), no dos
    assert v.doc.resultados[-1].estado == "ok"
    for tecla, quedan in ((Qt.Key_Z, pasos), (Qt.Key_Y, pasos + 1)):
        v.activateWindow()          # Xvfb no tiene gestor de ventanas: no devuelve el foco al cerrarse la barra
        QTest.qWaitForWindowActive(v, 2000)
        assert _vuelve_enseguida(lambda t=tecla: QTest.keyClick(v.visor, t, Qt.ControlModifier)) < 0.25
        _esperar(lambda q=quedan: len(v.doc.operaciones) == q and not v.doc._esperando_hijo)
    assert not v.timeline.espera.isVisible()


@pytest.mark.parametrize("como", ["cancelar", "esc"])
def test_fl3b_cancelar_aceptar_deja_el_documento_como_estaba(monkeypatch, ventana, como):
    v = ventana
    panel = _panel_mover(v)
    receta = v.doc.a_dict()
    monkeypatch.setattr(aislado._Trabajador, "_avisar", lambda self, tarea: None)   # un proceso aparte que no contesta
    monkeypatch.setattr(aislado, "PLAZO_RECIBIR", 10 ** 6)
    aislado.cerrar_trabajador()
    v.doc._ultimo_prevuelo = None               # que Aceptar no reuse la previa: tiene que calcular aparte
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    QTest.qWait(300)
    assert v.timeline.espera.isVisible() and not v.findChildren(QProgressDialog)    # abajo, sin ventana encima
    if como == "esc":
        QTest.keyClick(v.visor, Qt.Key_Escape)
    else:
        QTest.mouseClick(v.timeline.cancelar_espera, Qt.LeftButton)
    _esperar(lambda: not v.timeline.espera.isVisible() and not v.doc._esperando_hijo, 10)
    QTest.qWait(200)
    assert v.doc.a_dict() == receta and v.panel is None and not v.doc.puede_rehacer()


def _raton(widget, tipo, pos, boton, botones):
    """Evento de mouse simulado (el cursor real no se mueve) que pasa por los filtros de la aplicación como uno de verdad."""
    QApplication.sendEvent(widget, QMouseEvent(tipo, QPointF(pos), QPointF(widget.mapToGlobal(pos)), boton, botones,
                                               Qt.NoModifier))


def test_p173_durante_el_calculo_aparte_la_camara_se_mueve_y_el_documento_no(monkeypatch, ventana):
    v = ventana
    panel = _panel_mover(v)
    receta = v.doc.a_dict()
    monkeypatch.setattr(aislado._Trabajador, "_avisar", lambda self, tarea: None)   # un proceso aparte que no contesta
    monkeypatch.setattr(aislado, "PLAZO_RECIBIR", 10 ** 6)
    aislado.cerrar_trabajador()
    v.doc._ultimo_prevuelo = None
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    QTest.qWait(300)
    assert v.timeline.espera.isVisible()
    vis, centro = v.visor, v.visor.rect().center()

    def camara():
        return vis.R.copy(), vis.objetivo.copy(), vis.distancia

    antes = camara()
    _raton(vis, QEvent.MouseButtonPress, centro, Qt.MiddleButton, Qt.MiddleButton)      # encuadre con el medio
    for d in (10, 30, 60):
        _raton(vis, QEvent.MouseMove, centro + QPoint(d, d // 2), Qt.NoButton, Qt.MiddleButton)
    _raton(vis, QEvent.MouseButtonRelease, centro + QPoint(60, 30), Qt.MiddleButton, Qt.NoButton)
    assert not np.array_equal(antes[1], camara()[1])
    distancia = vis.distancia
    QApplication.sendEvent(vis, QWheelEvent(QPointF(centro), QPointF(vis.mapToGlobal(centro)), QPoint(), QPoint(0, 120),
                                            Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
    assert vis.distancia != distancia                                                    # zoom con la rueda
    QTest.keyClick(vis, Qt.Key_Delete)                                                   # el teclado no toca el documento
    _raton(vis, QEvent.MouseButtonPress, centro, Qt.RightButton, Qt.RightButton)          # ni un menú contextual
    _raton(vis, QEvent.MouseButtonRelease, centro, Qt.RightButton, Qt.NoButton)
    QTest.qWait(100)
    assert v.timeline.espera.isVisible() and v.doc.a_dict() == receta and v.panel is panel
    QTest.keyClick(vis, Qt.Key_Escape)                                                   # Esc sigue cancelando
    _esperar(lambda: not v.timeline.espera.isVisible() and not v.doc._esperando_hijo, 10)
    QTest.qWait(200)
    assert v.doc.a_dict() == receta and v.panel is None and not v.doc.puede_rehacer()
