# -*- coding: utf-8 -*-
"""FL-3: abrir un proyecto no congela la ventana; el recálculo va al proceso aparte, las mallas se hacen en otro hilo y
Cancelar (o Esc) deja el documento de antes."""
import time

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QProgressDialog, QPushButton

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.nucleo import aislado
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _guardado_con_otra_version(tmp_path, monkeypatch):
    """Un proyecto cuya caché no sirve (guardado con otra versión): al abrirlo hay que recalcularlo entero."""
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 30, "width": 20, "height": 10})["ok"]
    assert api.llamar(s, "create_cylinder", {"radius": 5, "height": 20, "x": 60})["ok"]
    ruta = tmp_path / "pieza.omnicad"
    with monkeypatch.context() as m:
        m.setattr(proyecto, "VERSION", "0.0.0-otra")
        assert api.llamar(s, "save_document", {"path": str(ruta)})["ok"]
    return ruta


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 5, "width": 5, "height": 5, "name": "Viejo"})["ok"]
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
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


def test_fl3_abrir_vuelve_enseguida_y_el_proyecto_llega_despues(tmp_path, monkeypatch, ventana):
    ruta = _guardado_con_otra_version(tmp_path, monkeypatch)
    tareas, correr_json = [], aislado.correr_json
    monkeypatch.setattr(aislado, "correr_json", lambda tarea, *a, **k: tareas.append(tarea) or correr_json(tarea, *a, **k))
    viejo = ventana.doc
    inicio = time.perf_counter()
    ventana.abrir_ruta(str(ruta), aparte=True)
    assert time.perf_counter() - inicio < 0.25 and ventana.doc is viejo      # la ventana no esperó al recálculo
    _esperar(lambda: ventana.doc is not viejo)
    assert tareas == ["prevuelo_abrir"]          # 2 pasos: antes se recalculaba en el hilo de la ventana
    cuerpos = {c.id for c in ventana.doc.estado_final.cuerpos.values()}
    assert len(cuerpos) == 2 and ventana.doc.ruta == str(ruta)
    assert {m["id"] for m in ventana.visor._mallas} == cuerpos                # se ven, con las mallas del otro hilo


@pytest.mark.parametrize("como", ["cancelar", "esc"])
def test_fl3_cancelar_la_apertura_deja_el_documento_de_antes(tmp_path, monkeypatch, ventana, como):
    ruta = _guardado_con_otra_version(tmp_path, monkeypatch)
    monkeypatch.setattr(aislado._Trabajador, "_avisar", lambda self, tarea: None)   # un proceso aparte que no contesta
    monkeypatch.setattr(aislado, "PLAZO_RECIBIR", 10 ** 6)
    aislado.cerrar_trabajador()
    viejo = ventana.doc
    ventana.abrir_ruta(str(ruta), aparte=True)
    QTest.qWait(300)
    (espera,) = [d for d in ventana.findChildren(QProgressDialog) if d.isVisible()]
    if como == "esc":
        QTest.keyClick(espera, Qt.Key_Escape)
    else:
        QTest.mouseClick(espera.findChild(QPushButton), Qt.LeftButton)
    _esperar(lambda: not any(d.isVisible() for d in ventana.findChildren(QProgressDialog)), 10)
    QTest.qWait(200)
    assert ventana.doc is viejo and [c.nombre for c in viejo.estado_final.cuerpos.values()] == ["Viejo"]
