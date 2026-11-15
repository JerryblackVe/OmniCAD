# -*- coding: utf-8 -*-
"""FL-5: en un documento grande, agregar una primitiva como cuerpo nuevo (y deshacerla o rehacerla) se calcula en la
ventana; lo que tiene booleana sigue yendo al proceso aparte, y el trabajador se pone al día solo."""
import pytest

from omnicad import api
from omnicad.nucleo import aislado
from omnicad.nucleo import geometria as geo


def _llamar(s, nombre, **argumentos):
    r = api.llamar(s, nombre, argumentos)
    assert r["ok"], r
    return r


@pytest.fixture
def aparte(monkeypatch):
    """Cuenta los cálculos que van al proceso aparte, con un documento «grande» desde 3 pasos."""
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 3)
    pedidos, correr = [], aislado.correr_json
    monkeypatch.setattr(aislado, "correr_json", lambda tarea, *a, **k: pedidos.append(tarea) or correr(tarea, *a, **k))
    return pedidos


def _volumenes(s):
    return sorted(round(geo.volumen(c.forma), 3) for c in s.doc.estado_final.cuerpos.values())


def test_fl5_cajas_en_la_ventana_y_union_aparte_sobre_cuerpo_ya_modificado(aparte):
    s = api.Sesion()
    for k in range(3):
        _llamar(s, "create_box", length=5, width=5, height=5, x=10 * k)
    _llamar(s, "create_box", length=3, width=3, height=9, operation="join")       # el primer cuerpo ya modificado
    assert aparte == ["prevuelo_cambio"]
    unido = _volumenes(s)
    _llamar(s, "create_box", length=5, width=5, height=5, x=30)                  # barata: en la ventana
    _llamar(s, "undo")                                                            # nada que calcular
    _llamar(s, "redo")                                                            # vuelve la caja: en la ventana
    assert aparte == ["prevuelo_cambio"]
    assert _volumenes(s) == sorted(unido + [125.0])
    _llamar(s, "create_box", length=3, width=3, height=9, x=10, operation="join")  # booleana: aparte, con el hijo atrasado
    _llamar(s, "undo")                                                            # en la ventana: recorta doc._estados
    _llamar(s, "redo")                                                            # aparte otra vez (antes: «pasos incompletos»)
    assert aparte == ["prevuelo_cambio", "prevuelo_cambio", "recalcular_documento"]
    assert _volumenes(s) == [125.0, 125.0, 161.0, 161.0]
    assert all(geo.es_valida(c.forma) for c in s.doc.estado_final.cuerpos.values())
