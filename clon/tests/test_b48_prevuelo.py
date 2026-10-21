# -*- coding: utf-8 -*-
"""B-48: el prevuelo defiende el cambio de parámetros; no cura las caídas nativas de OCCT."""
import sys
import time

import pytest

from omnicad.nucleo import aislado, motor
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.parametros import TablaParametros


@pytest.fixture(autouse=True)
def opencascade():
    with motor.fijar_motor("opencascade"):
        yield


def _documento(cantidad=2):
    doc = Documento()
    doc.parametros.agregar("altura", "3 mm")
    for i in range(cantidad):
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="5", alto="altura", x=str(i * 4)))
    assert all(r.estado == "ok" for r in doc.resultados)
    return doc


def _tabla(doc):
    tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
    tabla.modificar("altura", "7 mm")
    return tabla


def _volumenes(doc):
    return [geo.volumen(c.forma) for c in doc.estado_final.cuerpos.values()]


def _instantanea(doc):
    return (doc.a_dict(), _volumenes(doc), list(doc._deshacer), list(doc._rehacer), doc.modificado)


def test_crash_nativo_no_toca_documento_ni_deshacer(monkeypatch):
    doc = _documento()
    # Conserva también una entrada real de rehacer: el prevuelo no debe vaciarla.
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja"))
    doc.deshacer()
    doc.modificado = False
    antes, parametros, estados = _instantanea(doc), doc.parametros, list(doc._estados)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c",
                                                                 "import os; os._exit(-1073741819)"])
    with pytest.raises(ErrorDocumento, match="error nativo"):
        doc.aplicar_parametros(_tabla(doc))
    assert doc.parametros is parametros
    assert doc._estados == estados
    assert _instantanea(doc) == antes
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())


def test_hijo_real_permite_cambio_y_volumen_correcto(monkeypatch):
    doc = _documento()
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    antes = len(doc._deshacer)
    original, salidas = aislado.correr_json, []

    def registrar(*args):
        salida = original(*args)
        salidas.append(salida)
        return salida

    monkeypatch.setattr(aislado, "correr_json", registrar)
    assert _volumenes(doc) == pytest.approx([30, 30])
    doc.aplicar_parametros(_tabla(doc))
    assert salidas == [{"errores": 0, "pasos": 2}]
    assert doc.parametros.valores()["altura"] == 7
    assert _volumenes(doc) == pytest.approx([70, 70])
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())
    assert len(doc._deshacer) == antes + 1


@pytest.mark.parametrize("motivo", ["chico", "suprimidos", "marcador", "omnikernel", "hijo"])
def test_omite_prevuelo_cuando_no_corresponde(monkeypatch, motivo):
    doc = _documento()
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 3 if motivo == "chico" else 2)
    if motivo == "suprimidos":
        doc.suprimir("op2")
    elif motivo == "marcador":
        doc.mover_marcador(1)
    elif motivo == "hijo":
        monkeypatch.setattr(aislado, "EN_HIJO", True)
    elif motivo == "omnikernel":
        # Solo prueba la decisión: conserva OCC para calcular las formas ya creadas.
        monkeypatch.setattr(motor, "motor_activo", lambda: "omnikernel")
        monkeypatch.setattr(doc, "recalcular", lambda desde: None)
    llamadas = []
    monkeypatch.setattr(aislado.subprocess, "run", lambda *args, **kwargs: llamadas.append(args))
    doc.aplicar_parametros(_tabla(doc))
    assert llamadas == []
    assert doc.parametros.valores()["altura"] == 7


def test_tope_del_hijo_no_toca_documento(monkeypatch):
    doc = _documento()
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "TOPE_PREVUELO_PARAMETROS", 0.1)
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c",
                                                                 "import time; time.sleep(60)"])
    with pytest.raises(ErrorDocumento, match="se cortó"):
        doc.aplicar_parametros(_tabla(doc))
    assert _instantanea(doc) == antes


def test_hijo_informa_errores_de_pasos_sin_rechazar_tabla(monkeypatch):
    doc = _documento()
    tabla = _tabla(doc)
    tabla.modificar("altura", "-1 mm")
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    salida = aislado.correr_json("prevuelo_parametros", {"receta": doc.a_dict(), "parametros": tabla.a_lista(),
                                                       "desde": doc._primer_afectado(tabla)}, 60)
    assert salida == {"errores": 2, "pasos": 2}
    assert doc.parametros.valores()["altura"] == 3
    doc.aplicar_parametros(tabla)
    assert doc.parametros.valores()["altura"] == -1
    assert [r.estado for r in doc.resultados] == ["error", "error"]


def test_costo_prevuelo_60_pasos(capsys):
    """Medición reproducible: el prevuelo incluye arranque, reconstrucción y ensayo; el recálculo real no."""
    doc = _documento(60)
    assert aislado.UMBRAL_PREVUELO_PARAMETROS == 60
    tabla = _tabla(doc)
    desde = doc._primer_afectado(tabla)
    inicio = time.perf_counter()
    doc._prevuelo_parametros(tabla, desde)
    prevuelo = time.perf_counter() - inicio
    doc.parametros = tabla
    inicio = time.perf_counter()
    doc.recalcular(desde)
    recalculo = time.perf_counter() - inicio
    assert _volumenes(doc) == pytest.approx([70] * 60)
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())
    with capsys.disabled():
        print(f"\nB-48: 60 pasos; prevuelo={prevuelo:.6f} s; recálculo real={recalculo:.6f} s", flush=True)
