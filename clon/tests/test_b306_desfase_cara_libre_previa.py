# -*- coding: utf-8 -*-
"""B-306: el desfase de una cara libre (el filete de una rosca modelada) tardaba minutos en la ventana.

La previa va a un proceso aparte y, si ese cálculo ya falló con los mismos valores, Aceptar no lo repite."""
import time

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo, referencias as refs
from omnicad.timeline.ops_modificar import OpDesfaseCara
from omnicad.ui.comando import PanelComando, hit_desde_ref
from omnicad.ui.comandos.modificar import CaraDesfase
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **argumentos):
    resultado = api.llamar(sesion, nombre, argumentos)
    assert resultado["ok"], resultado
    return resultado["result"]


@pytest.fixture
def ventana(tmp_path):
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=40, height=20, name="Caja")
    _llamar(s, "create_cylinder", height=20, radius=4, x=60, name="Eje")
    _llamar(s, "create_thread", faces="%CYLINDER", body="Eje", thread="M8", modeled=True)
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _cuerpo(v, nombre):
    return next(c for c in v.doc.estado_final.cuerpos.values() if c.nombre == nombre)


def test_la_previa_del_desfase_va_aparte_solo_con_caras_libres(ventana):
    eje, caja = _cuerpo(ventana, "Eje"), _cuerpo(ventana, "Caja")
    assert any(map(refs.cara_libre, geo.caras(eje.forma))) and not any(map(refs.cara_libre, geo.caras(caja.forma)))
    p = ventana.ejecutar_comando(CaraDesfase())
    assert p._previa_pesada(OpDesfaseCara("opX", caras=[{"cuerpo": eje.id}]))
    assert not p._previa_pesada(OpDesfaseCara("opX", caras=[{"cuerpo": caja.id}]))   # 6 caras planas: sigue en el proceso


def test_aceptar_no_repite_un_calculo_aparte_que_ya_fallo(ventana, monkeypatch):
    monkeypatch.setattr(PanelComando, "_previa_pesada", lambda *a: True)
    caja = _cuerpo(ventana, "Caja")
    p = ventana.ejecutar_comando(CaraDesfase())
    cara = geo.caras(caja.forma)[0]
    p._elegida(hit_desde_ref({"tipo": "cara", "cuerpo": caja.id, "firma": refs.firma_cara(cara)}, p.ctx.estado))
    p.set_valor("distancia", "-1000 mm")           # el núcleo lo rechaza (P-136: con 0 ya lo frena el comando, sin proceso aparte)
    p._t_previa.stop()
    p._calcular_previa()
    assert p._hijo_previa is not None
    fin = time.perf_counter() + 30
    while p._hijo_previa is not None and time.perf_counter() < fin:
        QTest.qWait(10)
    assert p._hijo_previa is None and not p._previa_ok and p.mensaje.text()
    pasos = len(ventana.doc.operaciones)
    p.aceptar()
    assert ventana.panel is p and len(ventana.doc.operaciones) == pasos    # el panel sigue abierto con el error
