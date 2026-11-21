# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_circulo_3p»: tres clics degenerados (puntos alineados o coincidentes)
no tumban la app ni dejan el boceto roto, y todo aviso es de un renglón. (La herramienta no tiene campos de
diálogo: se ejercitan los casos degenerados de sus tres puntos.)"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def _abrir(app_qt, puntos):
    lz = T._lienzo(app_qt, Boceto())
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.grab()
    lz.set_herramienta("circulo_3p")
    avisos.clear()
    for xy in puntos:
        T._clic(lz, *xy)
    lz.grab()
    return lz, avisos


def _circulos(lz):
    return [c for c in lz.b.curvas.values() if getattr(c, "tipo", None) == "circulo"]


def _sin_rotura(lz, avisos):
    assert lz.isVisible()
    try:
        from omnicad.restricciones import resolver

        r = resolver(lz.b)
        assert r.ok, avisos
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"resolver crashed: {e}")
    for m in avisos:
        assert "\n" not in m and "\r" not in m, m


def test_tres_puntos_validos_dibujan_un_circulo(app_qt):
    lz, avisos = _abrir(app_qt, [(0, 0), (10, 0), (5, 5)])
    _sin_rotura(lz, avisos)
    assert len(_circulos(lz)) == 1
    assert not avisos
    assert lz.clics == []


def test_tres_puntos_alineados_avisan_y_no_dibujan(app_qt):
    lz, avisos = _abrir(app_qt, [(0, 0), (10, 0), (5, 0)])
    _sin_rotura(lz, avisos)
    assert _circulos(lz) == []
    assert lz.clics == []
    assert len(avisos) == 1
    assert "alineados" in avisos[0].lower()


def test_dos_puntos_coincidentes_no_tumban_la_app(app_qt):
    lz, avisos = _abrir(app_qt, [(0, 0), (0, 0), (5, 5)])
    _sin_rotura(lz, avisos)
    # No debe quedar el boceto roto; puede o no crear curva, pero sin excepción.
    assert lz.clics == []