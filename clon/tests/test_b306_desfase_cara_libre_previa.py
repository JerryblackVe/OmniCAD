# -*- coding: utf-8 -*-
"""B-306: el desfase de una cara libre (el filete de una rosca modelada) tardaba minutos en la ventana.

La previa va a un proceso aparte y, si ese cálculo ya falló con los mismos valores, Aceptar no lo repite."""
import math
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


def test_aceptar_con_la_previa_aparte_calcula_el_paso_aparte(ventana, monkeypatch):
    """Aceptar en plena previa aparte no calcula el paso en la ventana (con una rosca eran minutos congelada)."""
    from omnicad.timeline.documento import Documento
    monkeypatch.setattr(PanelComando, "_previa_pesada", lambda *a: True)
    pedidos, real = [], Documento._solicitar_calculo
    monkeypatch.setattr(Documento, "_solicitar_calculo", lambda doc, t, d: pedidos.append(t) or real(doc, t, d))
    caja = _cuerpo(ventana, "Caja")
    antes = geo.volumen_exacto(caja.forma)
    p = ventana.ejecutar_comando(CaraDesfase())
    cara = next(c for c in geo.caras(caja.forma) if refs.firma_cara(c)["centro"][2] > 19.9)   # la tapa de arriba
    p._elegida(hit_desde_ref({"tipo": "cara", "cuerpo": caja.id, "firma": refs.firma_cara(cara)}, p.ctx.estado))
    p.set_valor("distancia", "2 mm")
    p._t_previa.stop()
    p._calcular_previa()
    assert p._hijo_previa is not None             # la previa sigue en vuelo
    p.aceptar()
    assert ventana.panel is None and pedidos == ["prevuelo_cambio"]
    assert ventana.doc.resultados[-1].estado == "ok"
    assert geo.volumen_exacto(_cuerpo(ventana, "Caja").forma) == pytest.approx(antes + 40 * 40 * 2)


def test_el_filete_de_una_rosca_se_rechaza_al_instante(ventana):
    """El kernel tardaba 89 s (1 mm) y 150 s (0,2 mm) en el filete de una M8 y fallaba: ahora el error es inmediato."""
    from omnicad.nucleo import solidos_modificar as sm
    eje = _cuerpo(ventana, "Eje")
    filete = next(c for c in geo.caras(eje.forma) if refs.cara_libre(c))
    inicio = time.perf_counter()
    with pytest.raises(geo.ErrorGeometria, match="Holgura impresión 3D"):
        sm.desfasar_caras(eje.forma, [filete], 0.2)
    assert time.perf_counter() - inicio < 5


def test_vaciar_un_cuerpo_con_rosca_falla_al_instante(ventana):
    """Gemelo: el vaciado de la M8 tardaba 124 s y fallaba con un mensaje de chaflanes que no venía al caso."""
    from omnicad.nucleo import solidos_modificar as sm
    eje = _cuerpo(ventana, "Eje")
    tapa = next(c for c in geo.caras(eje.forma) if refs.firma_cara(c)["geom"] == "plano")
    inicio = time.perf_counter()
    with pytest.raises(geo.ErrorGeometria, match="antes de hacer la rosca"):
        sm.vaciado(eje.forma, [tapa], espesor_interior=1.0)
    assert time.perf_counter() - inicio < 5


def test_en_un_cuerpo_con_rosca_la_cara_plana_sale_rapido_y_la_curva_falla_ya():
    """El kernel tardaba 93–95 s con cualquier cara de un cuerpo roscado: la plana salía recién después por la extrusión."""
    from omnicad.nucleo import solidos_modificar as sm
    s = api.Sesion()
    _llamar(s, "create_cylinder", height=10, radius=10, name="Base")
    _llamar(s, "create_cylinder", height=20, radius=4, z=10, name="Eje")
    _llamar(s, "create_thread", faces="%CYLINDER", body="Eje", thread="M8", modeled=True)
    _llamar(s, "boolean_operation", target="Base", tools=["Eje"], operation="join")
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    cil = next(c for c in geo.caras(forma) if refs.firma_cara(c)["geom"] == "cilindro" and refs.firma_cara(c)["area"] > 600)
    base = min((c for c in geo.caras(forma) if refs.firma_cara(c)["geom"] == "plano"), key=lambda c: refs.firma_cara(c)["centro"][2])
    inicio = time.perf_counter()
    with pytest.raises(geo.ErrorGeometria, match="rosca cosmética"):
        sm.desfasar_caras(forma, [cil], 0.1)
    antes = geo.volumen_exacto(forma)
    assert geo.volumen_exacto(sm.desfasar_caras(forma, [base], 0.5)) == pytest.approx(antes + math.pi * 100 * 0.5, rel=1e-4)
    assert time.perf_counter() - inicio < 10
