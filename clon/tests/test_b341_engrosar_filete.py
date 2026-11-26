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
from omnicad.nucleo.solidos_modificar import caras_en_cadena
from omnicad.nucleo.superficies import engrosar_superficie
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


def _previa_del_filete(ventana, cadena, operacion=None):
    eje = _cuerpo(ventana, "Eje")
    filete = next(c for c in geo.caras(eje.forma) if refs.cara_libre(c))
    p = ventana.ejecutar_comando(Engrosar())
    p._elegida(hit_desde_ref({"tipo": "cara", "cuerpo": eje.id, "firma": refs.firma_cara(filete)}, p.ctx.estado))
    p.set_valor("cadena", cadena)    # el panel la trae tildada: engrosaría toda la cadena tangente de la rosca
    p.set_valor("espesor", "0,5 mm")
    if operacion:
        p.set_valor("operacion", operacion)
    p._t_previa.stop()
    inicio = time.perf_counter()
    p._calcular_previa()
    assert time.perf_counter() - inicio < 2 and p._hijo_previa is not None      # antes: 17 s en la ventana
    fin = time.perf_counter() + 120
    while p._hijo_previa is not None and time.perf_counter() < fin:
        QTest.qWait(50)
    assert p._hijo_previa is None and p._previa_ok, (p.mensaje.text(), p.mensaje.toolTip())
    return p


def test_engrosar_el_filete_no_congela_la_ventana(ventana):
    _previa_del_filete(ventana, False)


def test_engrosar_la_cadena_del_filete_va_aparte_y_avisa(ventana):
    """B-630: con «Selección de cadena» (el valor del panel) la previa no espera el análisis de autointersecciones."""
    # «nuevo»: unir la cadena engrosada con el eje falla en el kernel (B-866), aparte de la espera de B-630
    p = _previa_del_filete(ventana, True, "nuevo")
    assert "Se comprueba al aceptar" in p.mensaje.text()


@pytest.mark.lento
def test_engrosar_superficie_de_la_cadena_de_la_rosca_aprueba_con_el_analisis_completo():
    """B-630: el análisis de la cadena de una rosca M8 tarda ~34 s; el plazo de Aceptar lo espera."""
    s = api.Sesion()
    _llamar(s, "create_cylinder", height=20, radius=4, name="Eje")
    _llamar(s, "create_thread", faces="%CYLINDER", body="Eje", thread="M8", modeled=True)
    eje = next(c for c in s.doc.estado_final.cuerpos.values() if c.nombre == "Eje")
    filete = next(c for c in geo.caras(eje.forma) if refs.cara_libre(c))
    cadena = caras_en_cadena(eje.forma, [filete])
    forma = engrosar_superficie(geo.compuesto(list(cadena)), 0.5)
    assert geo.es_valida(forma) and geo.volumen_exacto(forma) > 0


def test_aceptar_sigue_rechazando_si_el_analisis_no_llega(monkeypatch):
    """B-630: diferir el análisis es cosa de la previa: la herramienta (y Aceptar) no aprueban sin revisar."""
    from omnicad.nucleo import revision
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=50, height=20)
    _llamar(s, "shell", body="Cuerpo1", faces=">Z")
    caras = ["Cuerpo1/F6", "Cuerpo1/F4", "Cuerpo1/F9"]       # borde y dos paredes: la caja abierta de B-394
    monkeypatch.setattr(revision, "_autointersecciones_seguras", lambda forma, limite, plazo: (None, [], False))
    r = api.llamar(s, "thicken", {"faces": caras})
    assert not r["ok"] and "No se pudo comprobar" in r["mensaje"], r
    monkeypatch.setattr(revision, "_autointersecciones_seguras", lambda forma, limite, plazo: (2, [], True))
    r = api.llamar(s, "thicken", {"faces": caras})
    assert not r["ok"] and "probá menos espesor" in r["mensaje"], r
