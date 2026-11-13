# -*- coding: utf-8 -*-
"""BOC-49: el índice de ayudas reusa lo de las curvas que no cambiaron, y da lo mismo que armarlo de cero."""
import random

import numpy as np

from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.inferencia import Indice


def _boceto(n=60):
    b, azar, pids = Boceto(), random.Random(3), []
    for _ in range(n):
        x, y = azar.uniform(0, 100), azar.uniform(0, 100)
        a, c = b.agregar_punto(x, y), b.agregar_punto(x + azar.uniform(-9, 9), y + azar.uniform(-9, 9))
        b.agregar_linea(a, c)
        pids.append(a)
    b.agregar_circulo(b.agregar_punto(50, 50), 7)
    return b, pids


def _igual(a, b):
    assert a.cids == b.cids and a.prims == b.prims
    assert np.array_equal(a.cajas, b.cajas) and np.array_equal(a.lineas, b.lineas)
    assert a.refs == b.refs and np.array_equal(a.rx, b.rx) and a.duenos == b.duenos


def test_con_reuso_da_lo_mismo_que_de_cero_tras_mover_agregar_y_quitar():
    b, pids = _boceto()
    previo = Indice(b)
    b.puntos[pids[5]].x += 3.0                                   # una línea se mueve
    _igual(Indice(b, previo), Indice(b))
    previo = Indice(b, previo)
    a, c = b.agregar_punto(1, 1), b.agregar_punto(2, 5)
    b.agregar_linea(a, c)                                        # una curva nueva
    _igual(Indice(b, previo), Indice(b))
    previo = Indice(b, previo)
    b.quitar_curva(next(iter(b.curvas))) if hasattr(b, "quitar_curva") else b.curvas.pop(next(iter(b.curvas)))
    _igual(Indice(b, previo), Indice(b))


def test_reusa_las_curvas_que_no_cambiaron():
    b, pids = _boceto()
    previo = Indice(b)
    b.puntos[pids[0]].y += 1.0
    nuevo = Indice(b, previo)
    iguales = [c for c in nuevo.cids if nuevo._derivados[c][1] is previo._derivados[c][1]]
    assert len(iguales) >= len(nuevo.cids) - 2                    # solo la línea movida (y quizá su vecina) se recalcula
