# -*- coding: utf-8 -*-
"""B-155 y RS-X6: la previa pesada dice el motivo real y la atiende el trabajador, con su documento vivo."""
import json
import os
import sys
import time

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import aislado, geometria as geo
from omnicad.nucleo.aislado import CalculoPendiente, TareaAislada
from omnicad.timeline.calculo_aislado import leer_previa_visual, previa_visual
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva, operacion_desde_dict


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture(scope="module")
def placa():
    s = api.Sesion()
    _ok(s, "create_box", length=100, width=100, height=10)
    _ok(s, "create_hole", face=">Z", points=[[-20, 0, 10], [20, 0, 10]], diameter=20, through_all=True)
    arista = _ok(s, "find_edges", selector="%CIRCLE and >Z")["edges"][0]["id"]
    _ok(s, "fillet", edges=[arista], radius=5)
    empalme = s.doc.operaciones[-1].a_dict()
    _ok(s, "undo")
    _ok(s, "chamfer", edges=[arista], distance=2)
    chaflan = s.doc.operaciones[-1].a_dict()
    _ok(s, "undo")
    return s.doc, empalme, chaflan


@pytest.fixture(autouse=True)
def sin_trabajador():
    aislado.cerrar_trabajador()
    yield
    aislado.cerrar_trabajador()


def _variante(op, **params):
    return dict(op, params=dict(op["params"], **params))


def _datos(doc, op):
    return {"receta": doc.a_dict(), "operacion": op, "indice": None, "deflexion": 0.05, "angular": 0.5}


def _esperar(h, plazo=60):
    fin = time.monotonic() + plazo
    while time.monotonic() < fin:
        salida = h.sondear()
        if salida is not None:
            return salida
        time.sleep(0.01)
    pytest.fail("La previa no terminó")


def _pid():
    return aislado._trabajador.proceso.pid


def _malla(doc, salida):
    (v, n, seg), = leer_previa_visual(salida, doc.estado_final)[0]._mallas_previa.values()
    return v, n, seg


@pytest.mark.parametrize("caso", ["empalme", "chaflan"])
def test_un_valor_imposible_da_el_mismo_texto_que_en_el_proceso_principal(placa, caso):
    doc, empalme, chaflan = placa
    op = _variante(empalme, radio="32.329 mm") if caso == "empalme" else _variante(chaflan, distancia="60 mm")
    with pytest.raises(geo.ErrorGeometria) as principal:
        doc.previsualizar(operacion_desde_dict(op), None, en_vivo=True)
    with pytest.raises(TareaAislada) as aparte:
        _esperar(CalculoPendiente("previa_visual", _datos(doc, op)))
    assert str(aparte.value) == str(principal.value)
    assert "ErrorGeometria" not in str(aparte.value) and "código" not in str(aparte.value)
    assert caso != "empalme" or len(str(aparte.value)) > 200    # el texto entero, sin el corte a 200 de antes


def test_el_hijo_de_una_sola_tarea_da_el_mismo_texto(placa):
    doc, empalme, _ = placa
    op = _variante(empalme, radio="32.329 mm")
    with aislado._ocupado:                  # trabajador ocupado: la previa va a un hijo propio
        h = CalculoPendiente("previa_visual", _datos(doc, op))
    assert h.trabajador is None
    with pytest.raises(TareaAislada, match=r"^El empalme falló: el radio es demasiado grande.*de lo grande a lo chico"):
        _esperar(h)


def test_correr_json_con_un_hijo_propio_tampoco_corta_el_texto(placa):
    doc, empalme, _ = placa
    with aislado._ocupado, pytest.raises(TareaAislada, match=r"proceso aparte falló \(El empalme.*a lo chico.*\)"):
        aislado.correr_json("previa_visual", _datos(doc, _variante(empalme, radio="32.329 mm")), 60)


def test_una_salida_sin_detalle_no_muestra_un_codigo(placa, monkeypatch):
    doc, empalme, _ = placa
    monkeypatch.setattr(aislado, "_comando", lambda *a: [sys.executable, "-c", "raise SystemExit(1)"])
    with aislado._ocupado:
        h = CalculoPendiente("previa_visual", _datos(doc, empalme))
    with pytest.raises(TareaAislada) as e:
        _esperar(h)
    assert str(e.value) == "No se pudo calcular la vista previa: el proceso aparte falló (sin detalle)."


@pytest.mark.skipif(sys.platform != "win32", reason="el código de salida de una caída nativa es de Windows")
def test_una_caida_nativa_se_explica(placa, monkeypatch):
    doc, empalme, _ = placa
    monkeypatch.setattr(aislado, "_comando", lambda *a: [sys.executable, "-c", "import os; os._exit(-0x3FFFFFFB)"])
    with aislado._ocupado:
        h = CalculoPendiente("previa_visual", _datos(doc, empalme))
    with pytest.raises(TareaAislada, match="vista previa: el kernel cayó.*OmniCAD sigue andando"):
        _esperar(h)


def test_si_cae_el_trabajador_avisa_y_la_siguiente_arranca_otro(placa):
    doc, empalme, _ = placa
    h = CalculoPendiente("previa_visual", _datos(doc, empalme))
    pid = _pid()
    h.proceso.kill()
    with pytest.raises(TareaAislada, match=r"vista previa: el proceso aparte falló \(sin detalle\)"):
        _esperar(h)
    assert _esperar(CalculoPendiente("previa_visual", _datos(doc, empalme))) and _pid() != pid


def test_un_valor_bueno_despues_de_uno_malo_da_lo_mismo_que_un_hijo_nuevo(placa):
    doc, empalme, _ = placa
    bueno = _variante(empalme, radio="4 mm")
    _esperar(CalculoPendiente("previa_visual", _datos(doc, _variante(empalme, radio="5 mm"))))
    pid = _pid()
    with pytest.raises(TareaAislada, match="demasiado grande"):
        _esperar(CalculoPendiente("previa_visual", _datos(doc, _variante(empalme, radio="32.329 mm"))))
    salida = _esperar(CalculoPendiente("previa_visual", _datos(doc, bueno)))
    assert _pid() == pid
    con_trabajador = _malla(doc, salida)
    with aislado._ocupado:
        solo = _malla(doc, _esperar(CalculoPendiente("previa_visual", _datos(doc, bueno))))
    for a, b in zip(con_trabajador, solo, strict=True):
        assert np.array_equal(a, b)
    v_directo = _malla(doc, previa_visual(doc.a_dict(), bueno, None, 0.05, 0.5))[0]
    assert np.array_equal(con_trabajador[0], v_directo)


def test_la_segunda_previa_no_reconstruye_el_documento(placa, monkeypatch):
    """Corre `_atender` en este proceso, como el trabajador, para contar cuántas veces se arma el documento."""
    doc, empalme, _ = placa
    armados, recalculos = [], []
    desde_dict, recalcular = Documento.desde_dict, Documento.recalcular
    monkeypatch.setattr(Documento, "desde_dict", staticmethod(lambda d: armados.append(1) or desde_dict(d)))
    monkeypatch.setattr(Documento, "recalcular", lambda self, *a: recalculos.append(1) or recalcular(self, *a))
    monkeypatch.setattr(aislado, "formas_enviadas", {})
    monkeypatch.setattr(aislado, "huellas_enviadas", {})
    monkeypatch.setattr(aislado, "marca_enviada", None)
    monkeypatch.setattr(aislado, "documento_vivo", None)

    def pedir(radio):
        datos = json.loads(json.dumps(_datos(doc, _variante(empalme, radio=radio)), default=aislado._a_json))
        return aislado._atender("previa_visual", dict(datos, _marca=None, _cwd=os.getcwd()))

    assert "nodos" in pedir("5 mm")
    vivo, cuantos = aislado.documento_vivo, (len(armados), len(recalculos))
    assert vivo is not None and cuantos[0] == 1
    assert "demasiado grande" in pedir("32.329 mm")["_fallo"]
    assert "nodos" in pedir("4 mm")
    assert aislado.documento_vivo is vivo and (len(armados), len(recalculos)) == cuantos
    assert aislado.formas_enviadas == {} and aislado.marca_enviada is None    # el transporte de las ediciones sigue igual


def test_la_previa_no_toca_el_transporte_del_padre(placa):
    doc, empalme, _ = placa
    _esperar(CalculoPendiente("previa_visual", _datos(doc, empalme)))       # arrancar un trabajador borra esas tablas
    aislado.marca_recibida, aislado.formas_recibidas = "marca", {1: "forma"}
    salida = _esperar(CalculoPendiente("previa_visual", _datos(doc, empalme)))
    _malla(doc, salida)
    assert aislado.marca_recibida == "marca" and aislado.formas_recibidas == {1: "forma"}


@pytest.mark.parametrize("altura, solapa", [("5", True), ("100", False)])
def test_el_solape_de_extruir_sale_del_documento_vivo(placa, altura, solapa):
    doc, empalme, _ = placa
    _esperar(CalculoPendiente("previa_visual", _datos(doc, empalme)))
    pid = _pid()
    caja = OpPrimitiva("op90", forma="caja", ancho="30", largo="30", alto="3", z=altura).a_dict()
    h = CalculoPendiente("solape_herramienta", {"receta": doc.a_dict(), "operacion": caja, "indice": None,
                                                "cuerpos": list(doc.estado_final.cuerpos)})
    assert _esperar(h) == {"solapa": solapa} and _pid() == pid


def test_cancelar_no_mata_al_trabajador_y_la_otra_previa_espera_su_turno(placa):
    doc, empalme, _ = placa
    primera = CalculoPendiente("previa_visual", _datos(doc, _variante(empalme, radio="5 mm")))
    pid = _pid()
    primera.cancelar()
    segunda = CalculoPendiente("previa_visual", _datos(doc, _variante(empalme, radio="4 mm")))
    assert segunda.proceso is None                       # no pisa el pedido en curso ni arranca otro proceso
    salida = _esperar(segunda)
    assert _pid() == pid and aislado._previa_en_curso is None
    directa = _malla(doc, previa_visual(doc.a_dict(), _variante(empalme, radio="4 mm"), None, 0.05, 0.5))[0]
    assert np.array_equal(_malla(doc, salida)[0], directa)     # es la respuesta de la segunda, no la de la cancelada


def test_el_calculo_que_sigue_espera_a_la_previa_cancelada(placa):
    doc, empalme, _ = placa
    previa = CalculoPendiente("previa_visual", _datos(doc, empalme))
    pid = _pid()
    previa.cancelar()
    salida = aislado.correr_json("recalcular_documento", {"receta": doc.a_dict()}, 60)
    assert salida["pasos"] == 2 and _pid() == pid and aislado._previa_en_curso is None


def test_una_previa_cancelada_que_no_termina_se_corta_sola(placa, monkeypatch):
    doc, empalme, _ = placa
    monkeypatch.setattr(aislado, "PACIENCIA_PREVIA", 0.05)
    avisar = aislado._Trabajador._avisar
    monkeypatch.setattr(aislado._Trabajador, "_avisar", lambda self, tarea: None)      # nunca contesta
    h = CalculoPendiente("previa_visual", _datos(doc, empalme))
    proceso = h.proceso
    h.cancelar()
    fin = time.monotonic() + 5
    while proceso.poll() is None and time.monotonic() < fin:
        time.sleep(0.01)
    assert proceso.poll() is not None and aislado._previa_en_curso is None
    monkeypatch.setattr(aislado._Trabajador, "_avisar", avisar)
    assert _esperar(CalculoPendiente("previa_visual", _datos(doc, empalme)))


def test_una_previa_vigente_no_se_pisa_con_otro_pedido(placa, monkeypatch):
    doc, empalme, _ = placa
    pedidos = []
    correr = aislado._correr
    monkeypatch.setattr(aislado, "_correr", lambda *a, **k: pedidos.append(a[0]) or correr(*a, **k))
    h = CalculoPendiente("previa_visual", _datos(doc, empalme))
    assert aislado.correr_json("recalcular_documento", {"receta": doc.a_dict()}, 60)["pasos"] == 2
    assert pedidos == ["recalcular_documento"] and _esperar(h)      # un hijo aparte; la previa sigue intacta
