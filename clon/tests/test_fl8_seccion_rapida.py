# -*- coding: utf-8 -*-
"""FL-8: la tapa del Análisis de sección de una placa con muchos agujeros. El recorte de orejas recalculaba todo el
polígono en cada oreja y la probaba contra todos los vértices cóncavos: 1,1 s con 40 agujeros. Ahora usa una lista
enlazada y una grilla; el resultado es el mismo (n − 2 triángulos, ninguno invertido, el área del corte)."""
import time

import numpy as np
import pytest

from omnicad.nucleo import analisis as an
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml


def _areas(xy, tris):
    T = xy[tris]
    return 0.5 * ((T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) - (T[:, 1, 1] - T[:, 0, 1]) * (T[:, 2, 0] - T[:, 0, 0]))


def test_fl8_la_tapa_de_una_placa_agujereada_cubre_el_corte():
    """Sobre un cuerpo ya modificado: la placa con 12 agujeros cortados uno por uno."""
    placa = geo.caja(120, 60, 10)
    for i in range(12):
        placa = geo.booleano(placa, geo.cilindro(3, 20, (10 + (i % 6) * 20, 15 + (i // 6) * 30, -5)), "cortar")
    plano = geo.Plano("XY", 5.0)
    tris = np.asarray(an.seccion_visual(placa, plano)["triangulos"], float)
    area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    assert area.sum() == pytest.approx(an.seccion(placa, plano)["area"], rel=0.01)
    assert (np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])[:, 2] > 0).all()     # todos del mismo lado


def test_fl8_cien_agujeros_triangulan_rapido_y_bien():
    a = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    anillos = [np.array([[0, 0], [100, 0], [100, 50], [50, 50], [50, 100], [0, 100]], float)]   # en L: tiene un cóncavo
    anillos += [np.c_[5 + (h % 10) * 9.5 + 3 * np.cos(a), 5 + (h // 10) * 9.5 + 3 * np.sin(a)][::-1]
                for h in range(100) if (h % 10) * 9.5 < 45 or (h // 10) * 9.5 < 45]
    xy = np.concatenate(anillos)
    ini = np.cumsum([0] + [len(k) for k in anillos])
    t = time.perf_counter()
    tris = ml._triangular_2d(xy, [list(range(ini[i], ini[i + 1])) for i in range(len(anillos))])
    dt = time.perf_counter() - t
    areas = _areas(xy, tris)
    hueco = sum(-ml._area_2d(k) for k in anillos[1:])
    assert len(tris) == len(xy) + 2 * (len(anillos) - 1) - 2           # n − 2, con los puentes de ida y vuelta
    assert (areas > -1e-9).all()
    assert areas.sum() == pytest.approx(7500 - hueco, rel=1e-9)
    assert dt < 1.0, dt                                                 # VPS cargada: antes 1,8 s, ahora 0,4 s
