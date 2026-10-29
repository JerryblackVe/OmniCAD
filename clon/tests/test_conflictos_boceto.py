# -*- coding: utf-8 -*-
"""B-111: el diagnóstico de qué choca no corre en el hilo de la ventana; el pintado no lo espera y «lo último gana»."""
import os
import threading
import time

import pytest
from _contornos import contorno_splines

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto as E  # noqa: E402


def _lienzo(n=2):
    QApplication.instance() or QApplication([])
    b, valores = contorno_splines(n, conflicto=True)
    lz = E.Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resolver()
    return lz


def _esperar(lz, tope=120.0):
    fin = time.monotonic() + tope
    while lz._conflictos is None and time.monotonic() < fin:
        QApplication.processEvents()
        time.sleep(0.01)
    assert lz._conflictos is not None, "el diagnóstico no llegó"


def test_pintar_no_espera_el_diagnostico_y_el_texto_llega_igual_que_esperando(monkeypatch):
    llamadas = []
    original = E.restricciones_en_conflicto
    monkeypatch.setattr(E, "restricciones_en_conflicto", lambda *a, **k: (llamadas.append(1), original(*a, **k))[1])
    lz = _lienzo()
    assert not lz.resultado.ok and lz._conflictos is None
    assert lz.conflictos_sin_esperar() == [] and lz.texto_conflictos() == ""       # no esperó: todavía nada
    assert lz.geometria_en_conflicto(esperar=False) == set()
    emitidos = []
    lz.cambio.connect(lambda: emitidos.append(1))
    _esperar(lz)
    assert emitidos and len(llamadas) == 1
    asincrono = (lz.texto_conflictos(), lz.geometria_en_conflicto(esperar=False))
    lz._conflictos = None
    esperado = (lz.texto_conflictos(esperar=True), lz.geometria_en_conflicto())
    assert asincrono == esperado and asincrono[0].startswith("Chocan:") and asincrono[1]


def test_lo_ultimo_gana(monkeypatch):
    suelta, corridas = threading.Event(), []

    def lento(copia, valores, cancelar=None):
        corridas.append(len(corridas))
        yo = corridas[-1]
        if yo == 0:
            suelta.wait(30)
            return ["viejo"]
        return ["nuevo"]
    monkeypatch.setattr(E, "restricciones_en_conflicto", lento)
    lz = _lienzo()
    lz.conflictos_sin_esperar()              # arranca el diagnóstico 0 y queda esperando
    lz.resolver()                            # el boceto «cambió»: el diagnóstico 0 ya es de otra generación
    suelta.set()
    _esperar(lz)
    assert lz._conflictos == ["nuevo"] and len(corridas) == 2


def test_el_tope_de_tiempo_abandona_y_lo_dice(monkeypatch):
    monkeypatch.setattr(E, "TOPE_DIAGNOSTICO_S", -1.0)
    lz = _lienzo(3)
    lz.conflictos_sin_esperar()
    _esperar(lz)
    assert lz._conflictos == [] and "no se pudo ver cuál sobra" in lz.texto_conflictos()


def test_a_pedido_espera_y_da_lo_mismo():
    lz = _lienzo()
    assert lz.conflictos and lz.texto_conflictos(esperar=True).startswith("Chocan:")


@pytest.mark.parametrize("n", [2])
def test_f5_avisa_que_calcula_y_luego_el_resultado(n):
    lz = _lienzo(n)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    assert lz.mostrar_conflictos().startswith("Calculando")
    _esperar(lz)
    assert mensajes[0].startswith("Calculando") and mensajes[-1].startswith("Chocan:")
