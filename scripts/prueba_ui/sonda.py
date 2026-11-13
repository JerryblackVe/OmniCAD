# -*- coding: utf-8 -*-
"""Sonda de fluidez (FL-0): mide cuánto deja la app sin responder cada acción simulada de una prueba.

Una prueba de ventana despacha eventos con `QTest.mouseClick`, `keyClicks`, `QApplication.sendEvent`…: el manejador de
la app corre ADENTRO de esa llamada, en el hilo de la ventana, así que lo que tarda la llamada es lo que la persona vería
congelado. `QTest.qWait(ms)` solo espera: lo que pasa de `ms` es una demora del bucle de eventos. Lo que el guion de la
prueba hace entre llamadas (armar la escena con la API, leer resultados) NO se mide: no lo causa la ventana.
Umbral del evento: 100 ms (como `registro_uso`); una prueba falla con una acción de más de 1 s (`TOPE_MS`).
`OMNICAD_FLUIDEZ=aviso` solo informa; `=apagado` no instala nada. Se instala sola desde `arnes.iniciar`."""
import os
import time

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

UMBRAL_MS = 100.0           # lo que se anota (el umbral del evento `bloqueo_ui` de la app)
TOPE_MS = 1000.0            # lo que hace fallar a la pieza
BLOQUEOS = []               # (nombre, ms, instante)
_INSTALADA = False
_ORIGINALES = {}
_PROFUNDIDAD = 0            # una acción dentro de otra (un click que dispara sendEvent) se cuenta una sola vez


def modo():
    return os.environ.get("OMNICAD_FLUIDEZ", "falla")


def _medir(nombre, funcion, es_espera=False):
    def envoltura(*a, **k):
        global _PROFUNDIDAD
        if _PROFUNDIDAD:
            return funcion(*a, **k)
        _PROFUNDIDAD += 1
        t = time.perf_counter()
        try:
            return funcion(*a, **k)
        finally:
            _PROFUNDIDAD -= 1
            ms = (time.perf_counter() - t) * 1000.0
            if es_espera and a:
                ms -= float(a[0] if not hasattr(a[0], "isVisible") else a[1])     # qWait(ms) / qWait(widget, ms)
            if ms > UMBRAL_MS:
                BLOQUEOS.append((nombre, round(ms), time.time()))
    return envoltura


def instalar():
    global _INSTALADA
    if _INSTALADA or modo() == "apagado":
        return
    for nombre in ("mouseClick", "mouseDClick", "mousePress", "mouseRelease", "mouseMove", "keyClick", "keyClicks",
                   "keyPress", "keyRelease", "keyEvent"):
        if hasattr(QTest, nombre):
            _ORIGINALES[("QTest", nombre)] = getattr(QTest, nombre)
            setattr(QTest, nombre, _medir(f"QTest.{nombre}", getattr(QTest, nombre)))
    _ORIGINALES[("QTest", "qWait")] = QTest.qWait
    QTest.qWait = _medir("QTest.qWait", QTest.qWait, es_espera=True)
    _ORIGINALES[("QApplication", "sendEvent")] = QApplication.sendEvent
    QApplication.sendEvent = staticmethod(_medir("QApplication.sendEvent", QApplication.sendEvent))
    _INSTALADA = True


def graves():
    return [b for b in BLOQUEOS if b[1] > TOPE_MS]


def resumen():
    """(texto, ok): cuántas acciones pasaron de 100 ms y de 1 s, y las peores; `ok` es False con alguna de más de 1 s."""
    peores = sorted(BLOQUEOS, key=lambda b: -b[1])[:5]
    detalle = "; ".join(f"{n} {ms} ms" for n, ms, _ in peores)
    texto = f"{len(BLOQUEOS)} de más de {UMBRAL_MS:g} ms, {len(graves())} de más de {TOPE_MS:g} ms" + (f" · peores: {detalle}" if detalle else "")
    return texto, not graves() or modo() == "aviso"
