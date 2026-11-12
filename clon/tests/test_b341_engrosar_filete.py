# -*- coding: utf-8 -*-
"""B-341: Engrosar (17 s) y Desfase de superficie (6 s) sobre el filete de una rosca modelada calculaban la previa en la
ventana, congelada. Andan (no hay que rechazarlos, como el desfase de caras de B-306): la previa va al proceso aparte."""
import time

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo, referencias as refs
from omnicad.timeline.ops_superficie import OpEngrosar, OpSupDesfase
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.superficie import Engrosar
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **argumentos):
    r = api.llamar(sesion, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


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


def test_engrosar_y_desfase_de_superficie_de_un_filete_van_aparte(ventana):
    eje, caja = _cuerpo(ventana, "Eje"), _cuerpo(ventana, "Caja")
    p = ventana.ejecutar_comando(Engrosar())
    for clase in (OpEngrosar, OpSupDesfase):
        assert p._previa_pesada(clase("opX", caras=[{"cuerpo": eje.id}]))
        assert not p._previa_pesada(clase("opX", caras=[{"cuerpo": caja.id}]))     # 6 caras planas: en la ventana


def test_engrosar_el_filete_no_congela_la_ventana(ventana):
    eje = _cuerpo(ventana, "Eje")
    filete = next(c for c in geo.caras(eje.forma) if refs.cara_libre(c))
    p = ventana.ejecutar_comando(Engrosar())
    p._elegida(hit_desde_ref({"tipo": "cara", "cuerpo": eje.id, "firma": refs.firma_cara(filete)}, p.ctx.estado))
    p.set_valor("espesor", "0,5 mm")
    p._t_previa.stop()
    inicio = time.perf_counter()
    p._calcular_previa()
    assert time.perf_counter() - inicio < 2 and p._hijo_previa is not None      # antes: 17 s en la ventana
    fin = time.perf_counter() + 120
    while p._hijo_previa is not None and time.perf_counter() < fin:
        QTest.qWait(50)
    assert p._hijo_previa is None and p._previa_ok, p.mensaje.text()
