# -*- coding: utf-8 -*-
"""FL-3c: con el puente en vivo, un paso nuevo se calcula en el proceso aparte (`Documento.nuevos_aparte`) y las mallas
se hacen en otro hilo antes de avisarle a la ventana (`PuenteAgentes._mallar_en_hilo`). Si el proceso aparte falla, el
paso se calcula como siempre; se prueba sobre un cuerpo ya modificado (un cilindro con chaflán)."""
import os
import threading

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api import protocolo_puente as proto  # noqa: E402
from omnicad.nucleo import aislado  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.timeline.documento import Documento, ErrorDocumento  # noqa: E402

UNIR = {"length": 6, "width": 6, "height": 6, "x": 3, "z": 27, "operation": "join"}


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _chaflanado(s):
    ok(s, "create_cylinder", radius=5, height=30)
    ok(s, "chamfer", edges=">Z", distance=1)
    return s


def _volumen(doc):
    (cuerpo,) = doc.estado_final.cuerpos.values()
    return geo.volumen_exacto(cuerpo.forma)


def _con_paso_nuevo(monkeypatch, falla=None):
    """Volumen y cálculos aparte de Unir una caja al cilindro chaflanado, con `nuevos_aparte` prendido."""
    s, tareas, original = _chaflanado(api.Sesion()), [], Documento.calcular_aparte

    def calcular(doc, tarea, datos, esperar=None):
        tareas.append(tarea)
        if falla is not None:
            raise ErrorDocumento("el proceso aparte falló") from falla
        return original(doc, tarea, datos, esperar)

    monkeypatch.setattr(Documento, "calcular_aparte", calcular)
    s.doc.nuevos_aparte = True
    r = api.llamar(s, "create_box", UNIR)
    return s, r, tareas


def _normal():
    s = _chaflanado(api.Sesion())
    ok(s, "create_box", **UNIR)
    return _volumen(s.doc)


def test_fl3c_paso_nuevo_aparte_da_lo_mismo_que_en_la_ventana(monkeypatch):
    s, r, tareas = _con_paso_nuevo(monkeypatch)
    assert r["ok"], r
    assert tareas == ["prevuelo_cambio"]
    assert _volumen(s.doc) == pytest.approx(_normal(), rel=1e-9)


def test_fl3c_si_el_proceso_aparte_falla_cae_al_calculo_de_siempre(monkeypatch):
    s, r, tareas = _con_paso_nuevo(monkeypatch, aislado.TareaAislada("se cayó"))
    assert r["ok"], r
    assert tareas == ["prevuelo_cambio"]
    assert _volumen(s.doc) == pytest.approx(_normal(), rel=1e-9)


def test_fl3c_cancelar_no_cae_al_calculo_de_siempre(monkeypatch):
    s, r, _ = _con_paso_nuevo(monkeypatch, aislado.Cancelado("lo cancelaste"))
    assert not r["ok"]
    assert len(s.doc.operaciones) == 2          # cilindro y chaflán: la caja no entró


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    carpeta = tmp_path_factory.mktemp("fl3c")
    anterior = os.environ.get(proto.VARIABLE_CARPETA)
    os.environ[proto.VARIABLE_CARPETA] = str(carpeta)          # nunca el puente.json real del usuario
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)
    if anterior is None:
        os.environ.pop(proto.VARIABLE_CARPETA, None)
    else:
        os.environ[proto.VARIABLE_CARPETA] = anterior


def test_fl3c_el_puente_malla_en_otro_hilo_y_avisa_una_vez(ventana, monkeypatch):
    from omnicad.ui.puente import PuenteAgentes
    ventana.set_documento(Documento())
    puente = PuenteAgentes(ventana)
    for nombre, args in (("create_cylinder", {"radius": 5, "height": 30}), ("chamfer", {"edges": ">Z", "distance": 1})):
        assert puente.ejecutar(nombre, args)["ok"]
    hilos, avisos, original = [], [], ventana.visor.datos_cuerpo

    def datos_cuerpo(forma, *a, **k):
        hilos.append(threading.current_thread() is threading.main_thread())
        return original(forma, *a, **k)

    monkeypatch.setattr(ventana.visor, "datos_cuerpo", datos_cuerpo)
    ventana.doc.suscribir(oyente := lambda: avisos.append(True))
    try:
        r = puente.ejecutar("create_box", UNIR)
    finally:
        ventana.doc.desuscribir(oyente)
    assert r["ok"], r
    assert hilos == [False]                      # la malla del cuerpo unido, fuera del hilo de la ventana
    assert avisos == [True]                      # los oyentes, una sola vez y al final
    assert not ventana.doc.nuevos_aparte and not ventana.doc.diferir_avisos
    (cuerpo,) = ventana.doc.estado_final.cuerpos.values()
    assert id(cuerpo.forma) in ventana.visor._cache


def test_fl3c_el_trabajador_anota_el_avance_del_recalculo():
    s = _chaflanado(api.Sesion())
    ok(s, "create_box", **UNIR)
    aislado.correr_json("recalcular_documento", {"receta": s.doc.a_dict(), "sin_memoria": True}, 120)
    hechos, total = aislado.avance()          # lo último que anotó queda hasta el pedido siguiente
    assert total == 3 and 0 <= hechos < total
    aislado.correr_json("calentar", {"receta": Documento().a_dict()}, 120)     # sin pasos: no anota nada
    assert aislado.avance() is None               # el avance del pedido anterior se borró


def test_fl3c_la_barra_muestra_los_pasos_y_no_se_cierra_sola(ventana, monkeypatch):
    from PySide6.QtWidgets import QProgressDialog

    from omnicad.ui.ventana import _mostrar_avance
    espera = QProgressDialog("Abriendo…", "Cancelar", 0, 0, ventana)
    for dato, rango in ((None, (0, 0, 0)), ((40, 292), (0, 292, 40)), ((292, 292), (0, 292, 40))):
        monkeypatch.setattr(aislado, "avance", lambda d=dato: d)
        _mostrar_avance(espera)
        assert (espera.minimum(), espera.maximum(), max(espera.value(), 0)) == rango
    assert not espera.wasCanceled()
    espera.deleteLater()
