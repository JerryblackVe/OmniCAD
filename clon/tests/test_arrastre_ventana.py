# -*- coding: utf-8 -*-
"""B-111: en una parte grande del boceto el arrastre resuelve solo una ventana alrededor del punto; soltar resuelve todo."""
import math
import os

import pytest
from _contornos import contorno_splines

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import solver as S  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def _arrastre(base, valores, previo, pid, k, monkeypatch, ventana=True):
    """Seis movimientos de 0,4 mm en la dirección k y soltar (resolver todo). Devuelve (boceto, resultado, tamaños de
    los sistemas resueltos en los movimientos)."""
    monkeypatch.setattr(S, "UMBRAL_VENTANA", 40 if ventana else 10**9)
    tamanos, original = [], S._resolver_grupo
    monkeypatch.setattr(S, "_resolver_grupo", lambda sis, *a, **kw: (tamanos.append(len(sis.x0)), original(sis, *a, **kw))[1])
    b, (x0, y0) = base.copia(), base.coords(pid)
    for i in range(1, 7):
        b.puntos[pid].x, b.puntos[pid].y = x0 + 0.4 * i * math.cos(k), y0 + 0.4 * i * math.sin(k)
        assert S.resolver(b, valores, pid, previo).ok
    monkeypatch.setattr(S, "_resolver_grupo", original)
    return b, S.resolver(b, valores), tamanos


@pytest.mark.parametrize("k", range(5))
def test_soltar_deja_lo_mismo_que_el_arrastre_completo(k, monkeypatch):
    base, v = contorno_splines(20)
    previo = S.resolver(base, v)
    libres = [p for p in base.puntos if p not in base.puntos_fijos()]
    pid = libres[(7 * k + 5) % len(libres)]
    completo, rc, grande = _arrastre(base, v, previo, pid, k, monkeypatch, ventana=False)
    ventana, rv, chico = _arrastre(base, v, previo, pid, k, monkeypatch)
    assert max(chico) < max(grande) / 2                      # la ventana resuelve un sistema bastante menor
    assert rv.ok and rv.residuo_max < S.TOLERANCIA and rv.gdl == rc.gdl == previo.gdl
    assert rv.determinadas == rc.determinadas
    x, y = base.coords(pid)
    assert ventana.coords(pid) == pytest.approx((x + 2.4 * math.cos(k), y + 2.4 * math.sin(k)), abs=1e-9)
    assert max(math.dist(ventana.coords(p), completo.coords(p)) for p in base.puntos) < 1.0   # subdeterminado: caminos distintos (se midió hasta 0,6 mm)


def test_si_la_ventana_no_alcanza_se_amplia_y_vuelve_atras_lo_escrito(monkeypatch):
    base, v = contorno_splines(20)
    previo = S.resolver(base, v)
    pid = [p for p in base.puntos if p not in base.puntos_fijos()][5]
    original, tamanos = S._resolver_grupo, []

    def falla_la_primera(sis, *a, **kw):
        x, err, J, rango = original(sis, *a, **kw)
        tamanos.append(len(sis.x0))
        return x, (1.0 if len(tamanos) == 1 else err), J, rango      # la 1.ª ventana «no cumple»
    monkeypatch.setattr(S, "_resolver_grupo", falla_la_primera)
    x0, y0 = base.coords(pid)
    b = base.copia()
    b.puntos[pid].x, b.puntos[pid].y = x0 + 0.4, y0
    r = S.resolver(b, v, pid, previo)
    assert r.ok and len(tamanos) == 2 and tamanos[1] > tamanos[0]        # de la ventana a la parte entera
    assert r.sin_ventana                                                  # y los demás movimientos ya van directo
    b.puntos[pid].x += 0.4
    assert S.resolver(b, v, pid, r).ok and len(tamanos) == 3 and tamanos[2] == tamanos[1]
    assert S._Sistema(b, v, S._grupos(b)[0], fusionar=True).residuos(
        S._Sistema(b, v, S._grupos(b)[0], fusionar=True).x0).max() < S.TOLERANCIA


def test_sin_el_modulo_rust_da_lo_mismo(monkeypatch):
    """Respaldo Python (sin el .pyd o con uno viejo sin `spline_extremos`): mismo resultado."""
    base, v = contorno_splines(6)
    monkeypatch.setattr(S.nativo, "disponible", lambda: None)
    sin = S.resolver(base.copia(), v)
    monkeypatch.setattr(S.nativo, "disponible", lambda: object())          # un módulo viejo
    viejo = S.resolver(base.copia(), v)
    assert (sin.estado, sin.gdl, sin.residuo_max) == (viejo.estado, viejo.gdl, viejo.residuo_max)


# ---------------------------------------------------------------- el editor: Esc y Ctrl+Z
def _lienzo():
    QApplication.instance() or QApplication([])
    b, _ = contorno_splines(20)
    lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resize(900, 600)
    lz.resolver()
    lz.encuadrar()
    lz.set_herramienta("seleccionar")
    pid = next(p for p in lz.b.puntos if p not in lz.b.puntos_fijos() and not lz._determinada(p))
    return lz, pid


def _estado(lz):
    return {p: (q.x, q.y) for p, q in lz.b.puntos.items()}


def _arrastrar(lz, pid, soltar=True):
    p0 = lz.a_px(*lz.b.coords(pid)).toPoint()
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, p0)
    for i in range(1, 5):
        QTest.mouseMove(lz, p0 + QPoint(3 * i, -2 * i))
    if soltar:
        QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, p0 + QPoint(12, -8))


def test_esc_en_pleno_arrastre_deja_el_boceto_como_estaba():
    lz, pid = _lienzo()
    antes, pasos = _estado(lz), len(lz.historial)
    _arrastrar(lz, pid, soltar=False)
    assert lz._arrastre == pid and _estado(lz) != antes
    QTest.keyClick(lz, Qt.Key_Escape)
    assert lz._arrastre is None and _estado(lz) == antes and len(lz.historial) == pasos
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))     # soltar después de Esc no hace nada
    assert _estado(lz) == antes and len(lz.historial) == pasos


def test_ctrl_z_tras_soltar_deja_el_estado_previo_al_arrastre():
    lz, pid = _lienzo()
    antes, pasos = _estado(lz), len(lz.historial)
    _arrastrar(lz, pid)
    assert _estado(lz) != antes and len(lz.historial) == pasos + 1 and lz.resultado.ok
    lz.deshacer()                       # lo que dispara el atajo Ctrl+Z de la ventana (el Lienzo suelto no tiene atajos)
    despues = _estado(lz)
    assert len(lz.historial) == pasos
    assert max(math.dist(despues[p], antes[p]) for p in antes) < 1e-9


def test_si_el_punto_no_queda_donde_lo_puso_el_raton_no_vale_la_ventana(monkeypatch):
    """Cadena rígida (todos los lados iguales): arrastrar el extremo 50 mm obliga a mover la cadena entera; una ventana
    cumpliría las restricciones devolviendo el punto adonde estaba."""
    from omnicad.restricciones.boceto import Boceto
    b = Boceto()
    punto, lineas = b.agregar_punto(0, 0), []
    for i in range(60):
        extremo = b.agregar_punto(10 * ((i + 2) // 2), 10 * ((i + 1) // 2))
        linea = b.agregar_linea(punto, extremo)
        b.agregar_restriccion("horizontal" if i % 2 == 0 else "vertical", [linea])
        if lineas:
            b.agregar_restriccion("igual", [lineas[-1], linea])
        lineas.append(linea)
        punto = extremo
    cota = b.agregar_cota("distancia", [lineas[0]], "10")
    previo = S.resolver(b, {cota: 10})
    destino = (b.puntos[punto].x + 50, b.puntos[punto].y)
    b.puntos[punto].x, b.puntos[punto].y = destino
    r = S.resolver(b, {cota: 10}, arrastrado=punto, previo=previo)
    assert r.ok and r.sin_ventana and b.coords(punto) == pytest.approx(destino, abs=1e-3)
