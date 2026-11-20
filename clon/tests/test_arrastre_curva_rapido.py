# -*- coding: utf-8 -*-
"""Arrastrar una curva resuelve solo la parte del boceto que la contiene (como arrastrar un punto); si la curva une dos
partes, resuelve todo. Antes resolvía el boceto entero en cada evento del ratón (140 ms con 100 piezas)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def _lienzo(b):
    QApplication.instance() or QApplication([])
    lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resolver()
    llamadas = []
    original = lz.resolver
    lz.resolver = lambda arrastrado=None, rapido=False: (llamadas.append(rapido), original(arrastrado, rapido))[1]
    return lz, llamadas


def _mover(lz, cid, pasos=5):
    lz._ultimo = (0.0, 0.0)
    for i in range(1, pasos + 1):
        lz._mover_curva(cid, "mover", (0.7 * i, 0.4 * i))


def test_arrastrar_una_linea_resuelve_solo_su_parte_y_respeta_las_restricciones():
    b = Boceto()
    lados = b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_cota("distancia", [lados[0]], "20")
    otra = b.agregar_rectangulo((40, 0), (50, 10))          # otra parte: no se toca
    lz, llamadas = _lienzo(b)
    antes = {p: lz.b.coords(p) for c in otra for p in lz.b.curvas[c].puntos()}
    _mover(lz, lados[1])                                      # el lado derecho (vertical)
    assert llamadas == [True] * 5
    assert lz.resultado.ok
    a, c = (lz.b.coords(p) for p in lz.b.curvas[lados[0]].puntos())
    assert a[1] == pytest.approx(c[1], abs=1e-7) and abs(c[0] - a[0]) == pytest.approx(20, abs=1e-7)
    a, c = (lz.b.coords(p) for p in lz.b.curvas[lados[1]].puntos())
    assert a[0] == pytest.approx(c[0], abs=1e-7)              # sigue vertical
    assert {p: lz.b.coords(p) for c in otra for p in lz.b.curvas[c].puntos()} == antes
    lz.resolver()                                             # soltar: resolver todo da lo mismo
    assert lz.resultado.ok and lz.resultado.residuo_max < 1e-7


def test_una_linea_que_une_dos_partes_resuelve_todo():
    b = Boceto()
    r1 = b.agregar_rectangulo((0, 0), (10, 10))
    r2 = b.agregar_rectangulo((30, 0), (40, 10))
    puente = b.agregar_linea(b.curvas[r1[1]].p2, b.curvas[r2[3]].p2)   # sin restricciones propias
    lz, llamadas = _lienzo(b)
    _mover(lz, puente, 3)
    assert llamadas == [False] * 3
    assert lz.resultado.ok and lz.resultado.residuo_max < 1e-7


def test_la_grilla_de_textos_ocupados_da_lo_mismo_que_mirar_todas():
    import random

    from PySide6.QtCore import QRectF

    from omnicad.ui.editor_boceto_dibujo import _Ocupadas
    azar = random.Random(7)
    cajas = [QRectF(azar.uniform(-300, 300), azar.uniform(-300, 300), azar.uniform(1, 150), azar.uniform(1, 40))
             for _ in range(300)]
    ocupadas = _Ocupadas(cajas[:150])
    for caja in cajas[150:]:
        assert ocupadas.choca(caja) == any(caja.intersects(o) for o in cajas[:150])
    ocupadas.agregar(QRectF(1000, 1000, 5, 5))
    assert ocupadas.choca(QRectF(1003, 1003, 1, 1))
    assert not ocupadas.choca(QRectF(float("nan"), 0, 5, 5))      # no rompe el pintado


def test_a_px_con_visor_da_lo_mismo_que_proyectar():
    """P-182: `a_px` con la matriz plano × cámara en floats es `visor.proyectar` (planos girados y desplazados, puntos
    detrás de la cámara) y se rehace al cambiar la cámara."""
    import numpy as np

    from omnicad.ui.editor_boceto_base import LienzoBaseMixin
    from omnicad.ui.visor3d import Visor3D

    class _Visor:
        proyectar = Visor3D.proyectar

        def width(self):
            return 1500

        def height(self):
            return 950

    class _Lienzo(LienzoBaseMixin):
        pass

    azar = np.random.default_rng(3)
    detras = 0
    for plano in (g.Plano("XY"), g.Plano("YZ", 12.5), g.Plano("XZ", -4)):
        lz = _Lienzo()
        lz.visor, lz.plano = _Visor(), plano
        for _camara in range(3):                                   # cámara nueva: no se usa la matriz vieja
            lz._mvp = azar.normal(size=(4, 4))
            for x, y in azar.uniform(-200, 200, size=(40, 2)):
                w = (lz._mvp @ np.append(plano.a_3d(x, y), 1.0))[3]
                if abs(w) < 1e-6:
                    continue
                q, r = lz.visor.proyectar(plano.a_3d(x, y), lz._mvp), lz.a_px(x, y)
                if q is None:
                    detras += 1
                    assert (r.x(), r.y()) == (-1e5, -1e5)
                else:
                    assert r.x() == pytest.approx(q.x(), rel=1e-9, abs=1e-6)
                    assert r.y() == pytest.approx(q.y(), rel=1e-9, abs=1e-6)
    assert detras > 0
